# Plan de Futuras Optimizaciones para GOA

Este documento recopila propuestas técnicas para mantener el sistema de GOA rápido, seguro y eficiente a medida que crezca en número de estudiantes y profesores.

---

## 1. Límites de Capacidad y Control de Crecimiento

### A. Límite de 30 Alumnos por Código de Acceso
* **Objetivo:** Evitar que un solo código se sature o que se guarden partidas duplicadas/falsas sin límite.
* **Implementación:**
  * Al intentar ingresar el código o guardar la partida, contar los registros existentes en la tabla `resultados_estudiantes` para ese `codigo_acceso`.
  * Si la cantidad es $\ge 30$, bloquear el acceso y mostrar el mensaje: *"Este código de acceso ya alcanzó el límite máximo de 30 estudiantes. Por favor, solicita uno nuevo a tu docente."*

### B. Límite de Códigos Activos por Docente (ej: Máximo 5 o 10 códigos)
* **Objetivo:** Evitar la acumulación de códigos basura y obsoletos creados por accidente.
* **Implementación:**
  * Al hacer clic en "Generar código", verificar la cantidad de registros en `sesiones` para ese `id_profesor`.
  * Si ya tiene 10 códigos, bloquear la creación y sugerirle eliminar un código antiguo antes de crear uno nuevo.

### C. Limitar el Nombre del Estudiante (Máximo 30 caracteres)
* **Objetivo:** Evitar nombres extremadamente largos que puedan deformar las tablas del panel o sobrecargar el almacenamiento.
* **Implementación:**
  * Agregar una validación en el formulario web del estudiante y en el backend Flask:
    ```python
    if len(nombre_alumno) > 30:
        return jsonify({'success': False, 'error': 'El nombre debe tener un máximo de 30 caracteres.'}), 400
    ```

---

## 2. Optimizaciones de Base de Datos y Servidor

### A. Paginación en el Historial de Partidas
* **Objetivo:** Que el servidor no tenga que procesar todo el historial histórico cada vez que el docente abre el panel.
* **Implementación:**
  * Por defecto, cargar solo las últimas 30 partidas del docente.
  * Habilitar un botón en la interfaz de "Cargar más" o un buscador para filtrar por fechas o códigos específicos.

### B. Índices en la Base de Datos (SQL Indexes)
* **Objetivo:** Acelerar las búsquedas internas que realiza PostgreSQL.
* **Implementación:**
  * Ejecutar los siguientes comandos SQL una sola vez en la base de datos de Clever Cloud:
    ```sql
    CREATE INDEX idx_resultados_codigo ON resultados_estudiantes(codigo_acceso);
    CREATE INDEX idx_sesiones_profesor ON sesiones(id_profesor);
    ```

### C. Pool de Conexiones a Base de Datos
* **Objetivo:** No abrir y cerrar una conexión TCP/SSL en cada petición HTTP, lo cual consume alrededor de 300ms.
* **Implementación:**
  * Configurar `psycopg2.pool.SimpleConnectionPool` en `app.py` al iniciar el servidor Flask y tomar/devolver conexiones del pool en lugar de crear nuevas.
