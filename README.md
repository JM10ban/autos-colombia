# Autos Colombia – EA1

Prototipo académico web para gestionar usuarios, vehículos, entradas, salidas y celdas en un parqueadero por mensualidad.

## Requisitos
- Python 3.10 o superior
- Conexión a internet para instalar Flask la primera vez

## Ejecutar en Windows
1. Instala Python desde https://www.python.org/downloads/ y marca la opción **Add Python to PATH**.
2. Descomprime el ZIP.
3. Abre la carpeta del proyecto en Visual Studio Code.
4. Abre Terminal > New Terminal y ejecuta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Si PowerShell bloquea la activación, prueba:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

5. Abre http://127.0.0.1:5000 en el navegador.

## Flujo para probar
1. En Usuarios, registra un usuario.
2. En Vehículos, registra una placa asociada a ese usuario.
3. En Registrar entrada, introduce la placa; el sistema asigna una celda libre.
4. En Inicio, pulsa Registrar salida para cerrar la estancia y liberar la celda.
5. Revisa Celdas e Historial.

## Alcance
Este prototipo implementa la gestión básica de usuarios, vehículos, entradas, salidas, ocupación e historial. Las tablas de novedades y pagos están creadas, pero sus pantallas aún deben implementarse para completar el alcance total. La autenticación y los controles de seguridad de producción tampoco están implementados. No usar con datos reales ni desplegar públicamente sin reforzar seguridad, pruebas y configuración.
