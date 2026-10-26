
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-antes-de-usar-en-produccion"
DB_PATH = Path(__file__).with_name("autos_colombia.db")


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificacion TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            telefono TEXT,
            correo TEXT
        );

        CREATE TABLE IF NOT EXISTS vehiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            marca TEXT,
            color TEXT,
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS celdas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            estado TEXT NOT NULL DEFAULT 'disponible'
                CHECK(estado IN ('disponible','ocupada','fuera de servicio'))
        );

        CREATE TABLE IF NOT EXISTS estancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehiculo_id INTEGER NOT NULL,
            celda_id INTEGER NOT NULL,
            entrada TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            salida TEXT,
            observaciones TEXT,
            FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id),
            FOREIGN KEY(celda_id) REFERENCES celdas(id)
        );

        CREATE TABLE IF NOT EXISTS novedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estancia_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(estancia_id) REFERENCES estancias(id)
        );

        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            periodo TEXT NOT NULL,
            valor REAL NOT NULL CHECK(valor >= 0),
            fecha_pago TEXT,
            metodo TEXT,
            estado TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado IN ('pendiente','pagado','vencido')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );
        """)

        cantidad = con.execute(
            "SELECT COUNT(*) FROM celdas"
        ).fetchone()[0]

        if cantidad == 0:
            con.executemany(
                "INSERT INTO celdas(codigo) VALUES (?)",
                [(f"A-{n:02d}",) for n in range(1, 11)]
            )


@app.route("/")
def inicio():
    with db() as con:
        total_vehiculos = con.execute(
            "SELECT COUNT(*) FROM vehiculos"
        ).fetchone()[0]

        dentro = con.execute(
            "SELECT COUNT(*) FROM estancias WHERE salida IS NULL"
        ).fetchone()[0]

        libres = con.execute(
            "SELECT COUNT(*) FROM celdas WHERE estado='disponible'"
        ).fetchone()[0]

        estancias = con.execute("""
            SELECT e.id, v.placa, v.tipo, c.codigo,
                   e.entrada, u.nombre
            FROM estancias e
            JOIN vehiculos v ON v.id = e.vehiculo_id
            JOIN celdas c ON c.id = e.celda_id
            JOIN usuarios u ON u.id = v.usuario_id
            WHERE e.salida IS NULL
            ORDER BY e.entrada DESC
        """).fetchall()

    return render_template(
        "inicio.html",
        total_vehiculos=total_vehiculos,
        dentro=dentro,
        libres=libres,
        estancias=estancias
    )


@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    with db() as con:
        if request.method == "POST":
            identificacion = request.form.get(
                "identificacion", ""
            ).strip()
            nombre = request.form.get("nombre", "").strip()
            telefono = request.form.get("telefono", "").strip()
            correo = request.form.get("correo", "").strip()

            if not identificacion or not nombre:
                flash(
                    "Identificación y nombre son obligatorios.",
                    "error"
                )
            else:
                try:
                    con.execute("""
                        INSERT INTO usuarios
                        (identificacion, nombre, telefono, correo)
                        VALUES (?, ?, ?, ?)
                    """, (identificacion, nombre, telefono, correo))
                    con.commit()
                    flash("Usuario registrado correctamente.", "ok")
                    return redirect(url_for("usuarios"))
                except sqlite3.IntegrityError:
                    flash(
                        "Ya existe un usuario con esa identificación.",
                        "error"
                    )

        rows = con.execute(
            "SELECT * FROM usuarios ORDER BY nombre"
        ).fetchall()

    return render_template("usuarios.html", usuarios=rows)


@app.route("/vehiculos", methods=["GET", "POST"])
def vehiculos():
    with db() as con:
        if request.method == "POST":
            placa = request.form.get("placa", "").strip().upper()
            tipo = request.form.get("tipo", "Carro").strip()
            usuario_id = request.form.get("usuario_id", "").strip()
            marca = request.form.get("marca", "").strip()
            color = request.form.get("color", "").strip()

            if not placa or not usuario_id or not tipo:
                flash(
                    "La placa, el tipo y el usuario son obligatorios.",
                    "error"
                )
            else:
                try:
                    con.execute("""
                        INSERT INTO vehiculos
                        (placa, tipo, marca, color, usuario_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (placa, tipo, marca, color, usuario_id))
                    con.commit()
                    flash("Vehículo registrado correctamente.", "ok")
                    return redirect(url_for("vehiculos"))
                except sqlite3.IntegrityError:
                    flash(
                        "La placa ya existe o el usuario seleccionado "
                        "no es válido.",
                        "error"
                    )

        usuarios_lista = con.execute("""
            SELECT id, nombre, identificacion
            FROM usuarios
            ORDER BY nombre
        """).fetchall()

        rows = con.execute("""
            SELECT v.*, u.nombre AS nombre_usuario
            FROM vehiculos v
            JOIN usuarios u ON u.id = v.usuario_id
            ORDER BY v.placa
        """).fetchall()

    return render_template(
        "vehiculos.html",
        vehiculos=rows,
        usuarios=usuarios_lista
    )


@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    if request.method == "POST":
        placa = request.form.get("placa", "").strip().upper()
        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        with db() as con:
            vehiculo = con.execute(
                "SELECT * FROM vehiculos WHERE placa = ?",
                (placa,)
            ).fetchone()

            if not vehiculo:
                flash(
                    "No existe un vehículo registrado con esa placa.",
                    "error"
                )
                return redirect(url_for("entrada"))

            activa = con.execute("""
                SELECT id FROM estancias
                WHERE vehiculo_id = ? AND salida IS NULL
            """, (vehiculo["id"],)).fetchone()

            if activa:
                flash(
                    "Este vehículo ya tiene una entrada sin salida.",
                    "error"
                )
                return redirect(url_for("entrada"))

            celda = con.execute("""
                SELECT * FROM celdas
                WHERE estado = 'disponible'
                ORDER BY codigo
                LIMIT 1
            """).fetchone()

            if not celda:
                flash("No hay celdas disponibles.", "error")
                return redirect(url_for("entrada"))

            con.execute("""
                INSERT INTO estancias
                (vehiculo_id, celda_id, observaciones)
                VALUES (?, ?, ?)
            """, (vehiculo["id"], celda["id"], observaciones))

            con.execute(
                "UPDATE celdas SET estado = 'ocupada' WHERE id = ?",
                (celda["id"],)
            )
            con.commit()

            flash(
                f"Entrada registrada. Celda asignada: {celda['codigo']}.",
                "ok"
            )
            return redirect(url_for("inicio"))

    return render_template("entrada.html")


@app.route("/salida/<int:estancia_id>", methods=["POST"])
def salida(estancia_id):
    with db() as con:
        estancia = con.execute("""
            SELECT * FROM estancias
            WHERE id = ? AND salida IS NULL
        """, (estancia_id,)).fetchone()

        if not estancia:
            flash(
                "No se encontró una estancia activa para cerrar.",
                "error"
            )
            return redirect(url_for("inicio"))

        con.execute("""
            UPDATE estancias
            SET salida = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (estancia_id,))

        con.execute("""
            UPDATE celdas SET estado = 'disponible'
            WHERE id = ?
        """, (estancia["celda_id"],))

        con.commit()

    flash("Salida registrada y celda liberada.", "ok")
    return redirect(url_for("inicio"))


@app.route("/celdas")
def celdas():
    with db() as con:
        rows = con.execute("""
            SELECT c.*, v.placa
            FROM celdas c
            LEFT JOIN estancias e
                ON e.celda_id = c.id AND e.salida IS NULL
            LEFT JOIN vehiculos v ON v.id = e.vehiculo_id
            ORDER BY c.codigo
        """).fetchall()

    return render_template("celdas.html", celdas=rows)


@app.route("/historial")
def historial():
    placa = request.args.get("placa", "").strip().upper()

    with db() as con:
        rows = con.execute("""
            SELECT v.placa, u.nombre, c.codigo,
                   e.entrada, e.salida, e.observaciones
            FROM estancias e
            JOIN vehiculos v ON v.id = e.vehiculo_id
            JOIN usuarios u ON u.id = v.usuario_id
            JOIN celdas c ON c.id = e.celda_id
            WHERE v.placa LIKE ?
            ORDER BY e.entrada DESC
        """, (f"%{placa}%",)).fetchall()

    return render_template(
        "historial.html",
        estancias=rows,
        placa=placa
    )


@app.route("/novedades", methods=["GET", "POST"])
def novedades():
    with db() as con:
        if request.method == "POST":
            estancia_id = request.form.get(
                "estancia_id", ""
            ).strip()
            descripcion = request.form.get(
                "descripcion", ""
            ).strip()

            if not estancia_id or not descripcion:
                flash(
                    "Selecciona un movimiento y escribe la descripción.",
                    "error"
                )
            else:
                estancia = con.execute(
                    "SELECT id FROM estancias WHERE id = ?",
                    (estancia_id,)
                ).fetchone()

                if not estancia:
                    flash("El movimiento seleccionado no existe.", "error")
                else:
                    con.execute("""
                        INSERT INTO novedades (estancia_id, descripcion)
                        VALUES (?, ?)
                    """, (estancia_id, descripcion))
                    con.commit()
                    flash("Novedad registrada correctamente.", "ok")
                    return redirect(url_for("novedades"))

        movimientos = con.execute("""
            SELECT e.id, v.placa, u.nombre, e.entrada, e.salida
            FROM estancias e
            JOIN vehiculos v ON v.id = e.vehiculo_id
            JOIN usuarios u ON u.id = v.usuario_id
            ORDER BY e.entrada DESC
        """).fetchall()

        registros = con.execute("""
            SELECT n.id, n.descripcion, n.fecha,
                   v.placa, u.nombre, e.id AS estancia_id
            FROM novedades n
            JOIN estancias e ON e.id = n.estancia_id
            JOIN vehiculos v ON v.id = e.vehiculo_id
            JOIN usuarios u ON u.id = v.usuario_id
            ORDER BY n.fecha DESC
        """).fetchall()

    return render_template(
        "novedades.html",
        movimientos=movimientos,
        novedades=registros
    )


@app.route("/pagos", methods=["GET", "POST"])
def pagos():
    with db() as con:
        if request.method == "POST":
            usuario_id = request.form.get("usuario_id", "").strip()
            periodo = request.form.get("periodo", "").strip()
            valor_texto = request.form.get("valor", "").strip()
            metodo = request.form.get("metodo", "").strip()
            estado = request.form.get("estado", "pendiente").strip()
            fecha_pago = request.form.get("fecha_pago", "").strip() or None

            if not usuario_id or not periodo or not valor_texto:
                flash("Usuario, periodo y valor son obligatorios.", "error")
            elif estado not in ("pendiente", "pagado", "vencido"):
                flash("El estado seleccionado no es válido.", "error")
            else:
                try:
                    valor = float(valor_texto.replace(",", "."))

                    if valor < 0:
                        raise ValueError

                    if estado == "pagado" and not fecha_pago:
                        flash(
                            "Indica la fecha del pago cuando el estado sea pagado.",
                            "error"
                        )
                    else:
                        con.execute("""
                            INSERT INTO pagos
                            (usuario_id, periodo, valor, fecha_pago, metodo, estado)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            int(usuario_id), periodo, valor,
                            fecha_pago, metodo, estado
                        ))
                        con.commit()
                        flash("Pago registrado correctamente.", "ok")
                        return redirect(url_for("pagos"))

                except ValueError:
                    flash("Ingresa un valor numérico válido y no negativo.", "error")
                except sqlite3.IntegrityError:
                    flash("El usuario seleccionado no es válido.", "error")

        usuarios_lista = con.execute("""
            SELECT id, nombre, identificacion
            FROM usuarios
            ORDER BY nombre
        """).fetchall()

        registros = con.execute("""
            SELECT p.*, u.nombre, u.identificacion
            FROM pagos p
            JOIN usuarios u ON u.id = p.usuario_id
            ORDER BY p.id DESC
        """).fetchall()

        resumen = con.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN estado = 'pagado'
                    THEN valor ELSE 0 END), 0) AS recaudado,
                COALESCE(SUM(CASE WHEN estado = 'pendiente'
                    THEN valor ELSE 0 END), 0) AS pendiente,
                COALESCE(SUM(CASE WHEN estado = 'vencido'
                    THEN valor ELSE 0 END), 0) AS vencido
            FROM pagos
        """).fetchone()

    return render_template(
        "pagos.html",
        usuarios=usuarios_lista,
        pagos=registros,
        resumen=resumen
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
