# Manual de Usuario: Plataforma Educativa Ambiental GO-A

¡Bienvenido a **GO-A (Guardianes del Océano y el Ambiente)**! Esta guía detallada describe el funcionamiento, botones, interfaces y procesos iniciales de cada uno de los paneles del sistema, estructurado para **Estudiantes**, **Docentes** y **Administradores**.

---

## 🔗 Enlaces Rápidos y Recursos de Soporte

Para acceder a la plataforma en vivo y ver los videos explicativos en formato de tutoriales paso a paso, utiliza los siguientes enlaces:

* 🌐 **Plataforma Web Oficial (Producción):** [goa-wcnb.onrender.com](https://goa-wcnb.onrender.com)
* 📺 **Lista de Reproducción de Videos Tutoriales (YouTube):** [Tutoriales GO-A](https://youtube.com/playlist?list=PLEicLP17_e7c&si=abfnRF0KE0c8T350)
* 📖 **Manual de Usuario en Línea:** [goa-wcnb.onrender.com/manual](https://goa-wcnb.onrender.com/manual) (Una vez desplegado)

## 📖 Introducción al Proyecto

**GO-A (Guardianes del Océano y el Ambiente)** es un juego educativo interactivo diseñado especialmente para promover la cultura ambiental y el desarrollo sostenible en las escuelas de Cartagena de Indias. La plataforma permite a los estudiantes sumergirse en una aventura de aprendizaje basada en la toma de decisiones ecológicas, mientras proporciona a los docentes y administradores herramientas sólidas para el seguimiento escolar, administración de contenidos y evaluación pedagógica en tiempo real.

---
## 🎮 1. Modo Estudiante (Aventura de Aprendizaje)

Los estudiantes acceden al juego sin necesidad de registrarse con un correo electrónico. Acceden de forma temporal mediante un **Código de Acceso** proporcionado por su profesor.

### 🏁 Inicio y Onboarding
1. **Pantalla de Bienvenida (Splash Screen):** Al ingresar al sitio web, se muestra un logotipo flotante y un fondo con burbujas animadas. El alumno debe hacer clic en el botón **"Iniciar Aventura"** (esto activa los sonidos y la música del juego en el navegador).
2. **Video Introductorio:** Se reproduce automáticamente un video introductorio con sonido sobre el cuidado ambiental de Cartagena. El alumno puede presionar el botón **"Saltar ›"** en la esquina superior derecha si desea omitirlo.
3. **Selección de Modo:** Inicia la aventura presionando **"Comenzar Reto"** en la tarjeta **Modo Estudiante**.

---

### 📥 Pasos del Juego y Detalles de los Paneles

#### Paso 1: Acceso a la Partida
* **Descripción:** Ingreso del código alfanumérico generado por el docente.
* **Campos e Inputs:**
  * **Campo "Código de Partida":** Campo con icono de llave para ingresar los 6 caracteres. Auto-mayúsculas activo.
* **Botones y Comportamiento:**
  * **Botón "Continuar":** Se activa cuando el código de 6 caracteres es validado en el servidor.
  * **Tarjeta del Docente (Teacher Info Badge):** Revela con luz verde el nombre del profesor asignado (*“¡Código verificado! Eres estudiante del profesor/a: ...”*).

#### Paso 2: Identifícate
* **Descripción:** Panel para registrar el nombre del alumno.
* **Campos e Inputs:**
  * **Campo "Nombre y Apellido":** Máximo **14 caracteres** permitidos para evitar desbordamientos en los listados del docente.
* **Botones:**
  * **Botón "Ingresar a la Actividad":** Valida el nombre y accede al bloque temático.
  * **Botón "Volver Atrás":** Permite regresar al Paso 1 para cambiar el código.

#### Paso 3: Kit del Guardián (Material de Estudio)
* **Descripción:** 3 tarjetas informativas con animaciones y Text-to-Speech.
* **Componentes y Botones:**
  * **Tarjetas 1, 2 y 3:** Notas con bordes Azul, Verde y Naranja sobre reciclaje, agua y consumo responsable.
  * **Botón de Parlante "TTS":** El navegador lee mediante audio el contenido de las notas.
  * **Botón "Comenzar Evaluación":** Se activa únicamente después de mostrar las 3 notas completas.

#### Paso 4: Evaluación Inicial (5 Preguntas)
* **Descripción:** Cuestionario de 5 preguntas de selección múltiple.
* **Componentes e Interfaces:**
  * **Botones de Opción (A, B, C, D):** Al presionar una opción, se colorea de azul.
  * **Botón de Parlante:** Lector de voz para la pregunta actual.
  * **Botón "Siguiente Pregunta":** Se activa al responder y avanza en el examen.
  * **Botón Flotante "Cofre de Notas":** Esquina inferior derecha (icono de caja de herramientas). Abre un panel lateral (Drawer) con las 3 notas de estudio para consulta durante la prueba.

#### Paso 5: Transición a la Historia
* **Descripción:** Pantalla informativa de felicitación por el test.
* **Componentes y Botones:**
  * Muestra el **Título de la Historia** y la introducción del dilema del bloque.
  * **Botón "Entrar a la Historia"**: Transiciona a los nudos narrativos.

#### Paso 6: Historia Interactiva (3 Nudos/Escenas)
* **Descripción:** 3 escenas narrativas donde se toman decisiones ante problemas del colegio.
* **Componentes e Interfaces:**
  * **Lector de Voz (TTS):** Lector de audio de la situación narrada.
  * **Botones de Decisión (1, 2, 3):** Muestran la consecuencia de la acción tomada.
  * **Botón "Siguiente Escena" / "Ver Resultados":** Avanza al tomar decisiones.
  * **Cofre de Notas Flotante:** Sigue disponible en la esquina inferior derecha.

#### Paso 7: Resultados del Reto
* **Descripción:** Resumen de rendimiento guardado en PostgreSQL.
* **Componentes y Botones:**
  * **Círculo de Aciertos:** Puntuación final (ej: `7/8` aciertos).
  * **Desglose de Preguntas:** Tarjetas verdes (aciertos) y rojas (errores) con el feedback de cada pregunta o escena.
  * **Botón "Volver al Portal de Inicio":** Regresa al landing page y borra la sesión del navegador.

---

## 🏫 2. Portal del Docente (Seguimiento Escolar)

El docente gestiona el juego, genera códigos para sus estudiantes y descarga reportes de rendimiento.

### 🔑 Inicio de Sesión y Registro de Docentes
1. **Acceso:** Inicie sesión desde el menú de docentes.
2. **Registro:** Registro restringido a un máximo de **5 docentes** en todo el sistema. Requiere clave de al menos 6 caracteres y WhatsApp con formato `+57 3XXXXXXXXX`.
3. **Auto-recuperación de Clave:** Tras 3 intentos fallidos, se notifica automáticamente al administrador a través del sistema. El administrador se pondrá en contacto con el docente a través de WhatsApp (usando el número registrado en su cuenta) para brindarle soporte.

---

### 🎛️ Vista General del Panel del Docente

El panel cuenta con una barra lateral izquierda de navegación con las siguientes pestañas literales:

| Nombre de Pestaña en Interfaz | Funciones Principales |
| :--- | :--- |
| **Panel de Inicio y Diagnóstico** | Vista de estadísticas globales del grupo, porcentaje general de aciertos e indicadores de desempeño por temas. |
| **Generar Códigos de Acceso** | Creación y administración de los códigos de sesión de 6 caracteres, control de uso y asignación de bloques temáticos. |
| **Historial de Partidas** | Lista completa de exámenes de alumnos, buscadores, filtros de visualización y detalle individual de preguntas. |
| **Mi Perfil de Docente** | Configuración de los datos del docente, cambio de contraseña y datos de contacto de WhatsApp. |

---

### 🛠️ Funcionalidades y Botones por Panel (Docente)

#### A. Pestaña "Panel de Inicio y Diagnóstico"
* **Estadísticas de Diagnóstico:** Muestra el porcentaje de aciertos en cada bloque (Residuos, Agua, Energía, Liderazgo) para saber en qué temáticas flaquean más los estudiantes.

#### B. Pestaña "Generar Códigos de Acceso"
* **Botón "Generar Nuevo Código":** Genera un código de sesión de 6 caracteres. Límite máximo de **5 códigos activos** por docente.
* **Tarjetas de Código:** Rojas para códigos `Sin usar` y Azules para códigos `En uso`. Al pulsarlas, abre el **Modal de Detalles del Código**:
  * **Botón "Descargar Informe" (PDF):** Reporte formal listo para imprimir con logotipo oficial.
  * **Botón "Descargar Excel" (XLSX):** Exportación de notas del código a archivo Excel.
  * **Asignación de Bloque (Códigos sin usar):** Permite fijar un bloque específico para ese código (ej: *Bloque 2: Cuidado del Agua y Alcantarillado*).
  * **Botón "Eliminar Código" (Rojo):** Elimina el código y todos los resultados de los alumnos.

#### C. Pestaña "Historial de Partidas"
* **Buscador y Selector de Filtros:** Filtra por alumno, bloque o código de acceso.
* **Fila Clickable:** Al presionarla, abre el **Modal de Detalle del Estudiante** con estadísticas y barra bicolor de progreso.
  * **Descarga de Informes:** Botones para descargar el reporte del estudiante en PDF o en Excel.
  * **Desglose de Respuestas:** Muestra qué respondió el estudiante en cada una de las 8 etapas (test + historia) y su feedback.
* **Botón "Eliminar partida" (Papelera roja):** Borra únicamente el intento de ese estudiante.

#### D. Pestaña "Mi Perfil de Docente"
* **Perfil:** Configura el nombre público que verán los alumnos y el WhatsApp del docente.
* **Contraseña:** Cambia la contraseña ingresando la actual y la nueva contraseña.

---

## 👑 3. Portal del Administrador (Gestión Global del Sistema)

El administrador supervisa todo el sistema y gestiona el contenido escolar. Inicia sesión con el usuario `admin.goa`.

### 📌 Diferencias y Herramientas del Administrador

#### 1. Supervisión Centralizada
* En **Panel de Inicio y Diagnóstico**, **Generar Códigos de Acceso** e **Historial de Partidas**, visualiza y gestiona las partidas de todos los profesores del sistema.

#### 2. Campana de Soporte (Topbar)
* Permite atender solicitudes de docentes con inconvenientes de acceso con el botón <span class="btn-ref">WhatsApp</span> para abrir un chat directo con el profesor y ayudarle a restablecer su clave.

---

### 🖥️ Nuevas Pestañas de la Barra Lateral del Administrador

#### A. Pestaña "Creador de Historias y Contenido" (Editor de Contenido)
Asistente interactivo de 4 pasos para configurar los bloques (admite hasta 10 bloques en total):
1. **Paso 1: Bloque y Notas:** Modifica bloque, crea uno nuevo o elimínalo. Permite fijar título, icono (12 opciones), color temático (8 opciones) y redactar la Nota 1, Nota 2 y Nota 3 del Kit de estudio.
2. **Paso 2: Evaluación:** Edita las 5 preguntas evaluativas del test inicial, con 4 opciones de respuestas con sus feedbacks e indicando la correcta (1-4).
3. **Paso 3: Historia:** Configura el título general del relato, la introducción y edita 3 escenas o nudos (enunciado, 3 decisiones posibles con consecuencias/feedbacks e indicando la correcta 1-3).
4. **Paso 4: Guardar:** Guarda y aplica los cambios enviándolos al servidor en la nube con reindexación automática de IDs.

#### B. Pestaña "Gestión de Profesores"
* Muestra la tabla de docentes con sus usuarios, contraseñas, códigos, partidas y WhatsApp.
* Haga clic en un profesor para ver su desglose de códigos y alumnos.
* Pulse <span class="btn-ref">Eliminar Docente</span> para borrar la cuenta, códigos e historial de alumnos, reajustando la secuencia de IDs de los demás docentes en el sistema de manera automática.
