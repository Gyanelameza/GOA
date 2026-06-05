# GOA - Juego de Concientización Ambiental

Este repositorio contiene la base de datos y la lógica del panel de control de **GOA**, un juego educativo diseñado para fomentar la cultura ambiental en instituciones educativas de Cartagena.

## Estructura del Repositorio

El proyecto está organizado de la siguiente manera:

* **`database/`**: Contiene los scripts de la base de datos MySQL.
  * `Carga_Final_GOA.sql`: Creación de la base de datos `goa` y los inserts de los bloques 1, 2, 3 y 4.
* **`dashboard/`**: Contiene la lógica y la interfaz web del panel de control (construido con Flask).
  * `app.py`: Servidor backend en Python.
  * `templates/`: Archivos HTML para la interfaz.
  * `static/`: Estilos CSS y archivos JavaScript del cliente.

---

## Requisitos Previos

Asegúrate de tener instalado:
1. **Python 3.x**
2. **MySQL Server** (corriendo localmente)
3. Las dependencias de Python requeridas (puedes instalarlas usando pip).

---

## Configuración y Puesta en Marcha

### 1. Inicializar la Base de Datos
Para importar la base de datos en tu servidor local de MySQL:
1. Abre tu terminal de MySQL o una herramienta de gestión (como MySQL Workbench).
2. Ejecuta el archivo SQL de base de datos:
   ```sql
   source database/Carga_Final_GOA.sql;
   ```
   *(Esto creará la base de datos `goa`, las tablas y cargará todos los datos predeterminados).*

### 2. Iniciar el Dashboard Web
Para levantar el panel de control:
1. Abre tu terminal en la carpeta `dashboard`.
2. Instala los requerimientos:
   ```bash
   pip install Flask mysql-connector-python
   ```
3. Ejecuta el servidor:
   ```bash
   python app.py
   ```
4. Abre tu navegador e ingresa a `http://localhost:5000` para interactuar con la base de datos visualmente.
