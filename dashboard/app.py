from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
import psycopg2
import random
import string
import json

app = Flask(__name__)
app.secret_key = 'goa_secret_key_for_session_management_2026'

# Prevent aggressive browser caching of pages/assets
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-App-Version'] = '1.0.9'
    return response

DB_CONFIG = {
    'host': 'bdxdrafrcqpzcgr02qmo-postgresql.services.clever-cloud.com',
    'user': 'ubln8ics1lhzirt1xpmt',
    'password': 'pK5op6aVqeu4xD94M6a1aNLwxZzKs2',
    'database': 'bdxdrafrcqpzcgr02qmo',
    'port': 5432
}

def get_db_connection():
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Error al conectar a PostgreSQL: {e}")
        return None

def capitalize_name(name):
    if not name:
        return ''
    words = name.strip().split()
    return ' '.join(word.capitalize() for word in words)

def docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'profesor_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado. Inicie sesión como docente.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado. Inicie sesión como administrador.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def obtener_info_bloques():
    connection = get_db_connection()
    if not connection:
        return {}
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT bloque FROM (
                SELECT bloque FROM material_estudio
                UNION
                SELECT bloque FROM banco_preguntas
                UNION
                SELECT bloque FROM historia_interactiva
            ) as all_blocks ORDER BY bloque;
        """)
        bloques = [row[0] for row in cursor.fetchall()]
        
        info = {}
        for b in bloques:
            cursor.execute("SELECT contenido FROM material_estudio WHERE bloque = %s;", (b,))
            row = cursor.fetchone()
            title = ""
            if row and row[0]:
                lines = row[0].split('\n')
                if lines:
                    title = lines[0].strip()
            info[b] = title or f"Bloque {b}"
        return info
    except Exception as e:
        print(f"Error al obtener info de bloques: {e}")
        return {}
    finally:
        cursor.close()
        connection.close()

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'profesor_id' in session:
        return redirect(url_for('docente_panel'))
        
    error = None
    email = ''
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            email = data.get('usuario', data.get('email', '')).strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'docente').strip()
        else:
            email = request.form.get('usuario', request.form.get('email', '')).strip()
            password = request.form.get('password', '').strip()
            role = request.form.get('role', 'docente').strip()
            
        if not email or not password:
            error = "Por favor, llene todos los campos."
        else:
            if role == 'admin':
                # Map admin to admin.goa
                admin_username = 'admin.goa' if email.lower() in ['admin', 'admin.goa'] else email.lower()
                connection = get_db_connection()
                if not connection:
                    error = "No se pudo conectar a la base de datos."
                else:
                    cursor = connection.cursor()
                    try:
                        cursor.execute("SELECT id_profesor, contrasena, username, nombre FROM profesores WHERE username = %s;", (admin_username,))
                        admin_row = cursor.fetchone()
                        
                        # Check if it is the admin user
                        if admin_username == 'admin.goa':
                            if not admin_row:
                                # Create default admin entry in database if it doesn't exist
                                cursor.execute(
                                    "INSERT INTO profesores (contrasena, username, nombre) VALUES (%s, %s, %s) RETURNING id_profesor, contrasena, username, nombre;",
                                    ('admin', 'admin.goa', 'Administrador')
                                )
                                admin_row = cursor.fetchone()
                                connection.commit()
                            
                            # Validate password against database
                            if admin_row[1] == password:
                                session['profesor_id'] = admin_row[0]
                                session['profesor_nombre'] = 'Administrador'
                                session['profesor_email'] = admin_row[2]
                                session['profesor_nombre_publico'] = admin_row[3] if (admin_row[3] and admin_row[3].strip()) else admin_row[2]
                                session['admin_logged_in'] = True
                                session['failed_attempts'] = 0
                                
                                if request.is_json:
                                    return jsonify({'success': True, 'redirect': url_for('docente_panel')})
                                return redirect(url_for('docente_panel'))
                            else:
                                error = "Usuario o contraseña de administrador incorrectos."
                                session['failed_attempts'] = session.get('failed_attempts', 0) + 1
                                session['last_failed_username'] = admin_username
                        else:
                            error = "El usuario ingresado no tiene privilegios de administrador."
                            session['failed_attempts'] = session.get('failed_attempts', 0) + 1
                            session['last_failed_username'] = admin_username
                    except Exception as e:
                        if connection:
                            connection.rollback()
                        error = f"Error al iniciar sesión de administrador: {str(e)}"
                    finally:
                        cursor.close()
                        connection.close()
            else:
                # Docente role
                connection = get_db_connection()
                if not connection:
                    error = "No se pudo conectar a la base de datos."
                else:
                    cursor = connection.cursor()
                    try:
                        # Allow normal login, checking if it's admin logging in as docente
                        target_username = 'admin.goa' if email.lower() in ['admin', 'admin.goa'] else email
                        
                        cursor.execute("SELECT id_profesor, contrasena, username, nombre FROM profesores WHERE username = %s AND contrasena = %s;", (target_username, password))
                        profesor = cursor.fetchone()
                        if profesor:
                            session['profesor_id'] = profesor[0]
                            session['profesor_nombre'] = profesor[1]
                            session['profesor_email'] = profesor[2]
                            session['profesor_nombre_publico'] = profesor[3] if (profesor[3] and profesor[3].strip()) else profesor[2]
                            session['admin_logged_in'] = False  # Logged in as teacher
                            session['failed_attempts'] = 0
                            
                            # Clear notifications for this professor
                            try:
                                cursor.execute("DELETE FROM notificaciones WHERE id_profesor = %s;", (profesor[0],))
                                connection.commit()
                            except Exception as db_err:
                                print(f"Error deleting notifications on successful login: {db_err}")
                                connection.rollback()
                            
                            if request.is_json:
                                return jsonify({'success': True, 'redirect': url_for('docente_panel')})
                            return redirect(url_for('docente_panel'))
                        else:
                            error = "Credenciales incorrectas."
                            session['failed_attempts'] = session.get('failed_attempts', 0) + 1
                            session['last_failed_username'] = target_username
                            
                            # Check if the teacher exists
                            cursor.execute("SELECT id_profesor, nombre, whatsapp FROM profesores WHERE username = %s;", (target_username,))
                            teacher_exists = cursor.fetchone()
                            
                            if session['failed_attempts'] >= 5 and teacher_exists:
                                id_prof, name_prof, wa_prof = teacher_exists
                                # Check if a notification already exists for this teacher to prevent duplicates
                                cursor.execute("SELECT 1 FROM notificaciones WHERE id_profesor = %s LIMIT 1;", (id_prof,))
                                notification_exists = cursor.fetchone()
                                
                                if not notification_exists:
                                    try:
                                        cursor.execute("""
                                            INSERT INTO notificaciones (id_profesor, nombre, whatsapp)
                                            VALUES (%s, %s, %s);
                                        """, (id_prof, name_prof, wa_prof))
                                        connection.commit()
                                    except Exception as db_err:
                                        print(f"Error inserting auto-notification: {db_err}")
                                        connection.rollback()
                    except Exception as e:
                        error = f"Error en el servidor: {str(e)}"
                    finally:
                        cursor.close()
                        connection.close()
           
        if request.is_json:
            # Check teacher info for auto-recovery response
            connection = get_db_connection()
            teacher_info = None
            if connection:
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT nombre, whatsapp FROM profesores WHERE username = %s;", (session.get('last_failed_username', email),))
                    teacher_info = cursor.fetchone()
                finally:
                    cursor.close()
                    connection.close()

            attempts = session.get('failed_attempts', 0)
            response_data = {
                'success': False,
                'error': error,
                'failed_attempts': attempts
            }
            if attempts >= 5 and teacher_info:
                response_data['show_auto_recovery'] = True
                response_data['nombre'] = teacher_info[0]
                response_data['whatsapp'] = teacher_info[1]
                
            return jsonify(response_data), 401
            
    attempts = session.get('failed_attempts', 0)
    show_modal = False
    nombre = ""
    whatsapp = ""
    if attempts >= 5:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT nombre, whatsapp FROM profesores WHERE username = %s;", (session.get('last_failed_username', ''),))
                row = cursor.fetchone()
                if row:
                    show_modal = True
                    nombre = row[0]
                    whatsapp = row[1]
            finally:
                cursor.close()
                connection.close()

    return render_template('login.html', error=error, show_modal=show_modal, nombre=nombre, whatsapp=whatsapp, target_username=email)

@app.route('/api/reset-failed-attempts', methods=['POST'])
def reset_failed_attempts():
    session['failed_attempts'] = 0
    return jsonify({'success': True, 'failed_attempts': 0})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

MAX_PROFESORES = 5

@app.route('/api/registro-docente', methods=['POST'])
def registro_docente():
    """Register a new teacher. Max 5 teachers total in the system.
    Username (stored in email column) is auto-generated as nombre.profesor.
    """
    data = request.json or {}
    nombre         = (data.get('nombre',   '') or '').strip()
    password       = (data.get('password', '') or '').strip()
    nombre_publico = (data.get('nombre_publico', '') or nombre).strip()
    whatsapp       = (data.get('whatsapp', '') or '').strip()

    if not nombre or not password:
        return jsonify({'success': False, 'error': 'Por favor completa todos los campos.'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 6 caracteres.'}), 400
    if not whatsapp:
        return jsonify({'success': False, 'error': 'El número de WhatsApp es obligatorio.'}), 400

    import re
    # Validate name (no leading spaces, no special chars, numbers allowed)
    name_pattern = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+( [a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+)*$'
    if not re.match(name_pattern, nombre):
        return jsonify({'success': False, 'error': 'El nombre no puede tener espacios iniciales/finales ni caracteres especiales, pero se aceptan números.'}), 400
    if nombre_publico and not re.match(name_pattern, nombre_publico):
        return jsonify({'success': False, 'error': 'El nombre público no puede tener espacios iniciales/finales ni caracteres especiales.'}), 400

    # Validate WhatsApp (allow spaces in the middle)
    whatsapp_val = whatsapp.replace(' ', '')
    whatsapp_pattern = r'^\+573\d{9}$'
    if not re.match(whatsapp_pattern, whatsapp_val):
        return jsonify({'success': False, 'error': 'El número de WhatsApp debe comenzar con +57 y tener un número de 10 dígitos que comience con 3.'}), 400

    # Clean and format WhatsApp
    digits = re.sub(r'\D', '', whatsapp_val[3:])
    whatsapp_clean = f"+57 {digits}"

    # Auto-generate username: "laura gomez" -> "laura.gomez.profesor"
    import unicodedata
    def normalize(s):
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        s = s.lower().strip()
        s = re.sub(r'[^a-z0-9 ]', '', s)
        s = re.sub(r' +', '.', s)
        return s
    usuario = normalize(nombre) + '.profesor'

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500

    cursor = connection.cursor()
    try:
        # 1. Check total professor count
        cursor.execute("SELECT COUNT(*) FROM profesores;")
        total = cursor.fetchone()[0]
        if total >= MAX_PROFESORES:
            return jsonify({'success': False, 'error': f'Se ha alcanzado el límite máximo de {MAX_PROFESORES} docentes registrados en el sistema.'}), 403

        # 2. Check username uniqueness (stored in username column)
        cursor.execute("SELECT id_profesor FROM profesores WHERE username = %s;", (usuario,))
        if cursor.fetchone():
            return jsonify({'success': False, 'error': f'El usuario "{usuario}" ya está en uso. Prueba con un nombre diferente.'}), 409

        # 3. Insert new teacher (username col = auto-generated username; contrasena col = password; nombre col = display name)
        cursor.execute(
            "INSERT INTO profesores (contrasena, username, nombre, whatsapp) VALUES (%s, %s, %s, %s);",
            (password, usuario, nombre_publico, whatsapp_clean)
        )
        connection.commit()
        return jsonify({'success': True, 'usuario': usuario, 'message': '¡Registro exitoso! Ya puedes iniciar sesión.'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': f'Error en el servidor: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/cupos-docente', methods=['GET'])
def cupos_docente():
    """Return current and max teacher count (public endpoint for registration form)."""
    connection = get_db_connection()
    if not connection:
        return jsonify({'total': 0, 'maximo': MAX_PROFESORES}), 200
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM profesores;")
        total = cursor.fetchone()[0]
        return jsonify({'total': total, 'maximo': MAX_PROFESORES})
    except Exception as e:
        return jsonify({'total': 0, 'maximo': MAX_PROFESORES, 'error': str(e)}), 200
    finally:
        cursor.close()
        connection.close()

@app.route('/admin-db')
def admin_db():
    return render_template('dashboard.html')

@app.route('/api/tables', methods=['GET'])
def get_tables():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    
    cursor = connection.cursor()
    try:
        # Obtener lista de tablas filtrando solo las pertenecientes al proyecto GOA
        goa_tables = ('profesores', 'sesiones', 'resultados_estudiantes', 'banco_preguntas', 'historia_interactiva', 'material_estudio')
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN %s ORDER BY table_name;", (goa_tables,))
        tables_raw = cursor.fetchall()
        
        tables = []
        for item in tables_raw:
            table_name = item[0]
            # Obtener cantidad de filas por cada tabla
            cursor.execute(f'SELECT COUNT(*) as total FROM "{table_name}"')
            count_res = cursor.fetchone()
            tables.append({
                'name': table_name,
                'rows': count_res[0]
            })
            
        return jsonify({'tables': tables})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/table/<table_name>', methods=['GET'])
def get_table_data(table_name):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    
    cursor = connection.cursor()
    try:
        # Obtener columnas
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;", (table_name,))
        columns_raw = cursor.fetchall()
        columns = [col[0] for col in columns_raw]
        
        # Obtener filas
        cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 100')
        rows = cursor.fetchall()
        
        # Convertir filas a formato serializable
        serialized_rows = []
        for row in rows:
            serialized_row = []
            for val in row:
                if isinstance(val, bytes):
                    # Manejar bits/booleanos
                    serialized_row.append(int(val[0]) if val else 0)
                else:
                    serialized_row.append(str(val) if val is not None else None)
            serialized_rows.append(serialized_row)
            
        return jsonify({
            'columns': columns,
            'rows': serialized_rows
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/query', methods=['POST'])
def run_query():
    data = request.json
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'La consulta SQL no puede estar vacía.'}), 400
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        
        is_select = (query.lower().startswith('select') or 
                     query.lower().startswith('show') or 
                     query.lower().startswith('explain') or
                     query.lower().startswith('describe') or
                     query.lower().startswith('with'))
        
        if is_select:
            # Es una consulta de lectura
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            serialized_rows = []
            for row in rows:
                serialized_row = []
                for val in row:
                    if isinstance(val, bytes):
                        serialized_row.append(int(val[0]) if val else 0)
                    else:
                        serialized_row.append(str(val) if val is not None else None)
                serialized_rows.append(serialized_row)
                
            return jsonify({
                'type': 'select',
                'columns': columns,
                'rows': serialized_rows
            })
        else:
            # Es una consulta de escritura (INSERT, UPDATE, DELETE, etc.)
            connection.commit()
            return jsonify({
                'type': 'write',
                'affected_rows': cursor.rowcount,
                'message': f'Consulta ejecutada con éxito. Filas afectadas: {cursor.rowcount}'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

def obtener_detalles_completos(cursor, bloque, detalles_estudiante):
    # 1. Obtener las 5 preguntas del banco de preguntas para este bloque
    cursor.execute("""
        SELECT pregunta, respuesta_correcta 
        FROM banco_preguntas 
        WHERE bloque = %s 
        ORDER BY id_pregunta;
    """, (bloque,))
    preguntas_db = cursor.fetchall()
    
    # 2. Obtener los 3 nudos de la historia interactiva para este bloque
    cursor.execute("""
        SELECT escena_titulo, texto_situacion, respuesta_correcta 
        FROM historia_interactiva 
        WHERE bloque = %s 
        ORDER BY id_nodo;
    """, (bloque,))
    nudos_db = cursor.fetchall()
    
    # Construir lista de las 8 preguntas del bloque
    preguntas_bloque = []
    
    # Agregar las del banco (Iniciales)
    for p in preguntas_db:
        preguntas_bloque.append({
            'pregunta': p[0],
            'respuesta_correcta': p[1],
            'tipo': 'inicial'
        })
        
    # Agregar los nudos (Historia)
    for n in nudos_db:
        titulo = n[0]
        texto = n[1]
        pregunta_texto = f"{titulo}: {texto}" if titulo else texto
        preguntas_bloque.append({
            'pregunta': pregunta_texto,
            'respuesta_correcta': n[2],
            'tipo': 'historia'
        })
        
    # Función para limpiar palabras y comparar
    def get_clean_words(s):
        if not s:
            return set()
        s = s.replace('', 'a').replace('', 'e').replace('', 'i').replace('', 'o').replace('', 'u').replace('', 'n')
        words = []
        for w in s.split():
            clean = ''.join(c for c in w.lower() if c.isalnum())
            if clean:
                words.append(clean)
        return set(words)
        
    def matches_question(student_q, db_q_text):
        s_words = get_clean_words(student_q)
        db_words = get_clean_words(db_q_text)
        if not s_words or not db_words:
            return False
        intersection = s_words.intersection(db_words)
        return len(intersection) / len(s_words) >= 0.5

    # Alinear detalles del estudiante con las preguntas del bloque
    detalles_completos = []
    
    # Si detalles_estudiante no es una lista, convertirla o inicializarla
    if not isinstance(detalles_estudiante, list):
        detalles_estudiante = []
        
    for p_db in preguntas_bloque:
        match_estudiante = None
        for det in detalles_estudiante:
            if isinstance(det, dict) and 'pregunta' in det:
                if matches_question(det['pregunta'], p_db['pregunta']):
                    match_estudiante = det
                    break
                    
        if match_estudiante:
            detalles_completos.append({
                'pregunta': p_db['pregunta'],
                'correcta': match_estudiante.get('correcta', False),
                'opcion_elegida': match_estudiante.get('opcion_elegida', ''),
                'feedback': match_estudiante.get('feedback', ''),
                'tipo': p_db['tipo'],
                'respondida': True
            })
        else:
            detalles_completos.append({
                'pregunta': p_db['pregunta'],
                'correcta': None,  # Indica que no fue respondida
                'opcion_elegida': 'No respondida',
                'feedback': f'Esta pregunta del { "banco inicial" if p_db["tipo"] == "inicial" else "nudo de la historia" } no fue respondida en esta partida.',
                'tipo': p_db['tipo'],
                'respondida': False
            })
            
    # Agregar cualquier detalle del estudiante que no haya sido emparejado
    for det in detalles_estudiante:
        if isinstance(det, dict) and 'pregunta' in det:
            ya_emparejado = False
            for dc in detalles_completos:
                if dc['respondida'] and matches_question(det['pregunta'], dc['pregunta']):
                    ya_emparejado = True
                    break
            if not ya_emparejado:
                detalles_completos.append({
                    'pregunta': det['pregunta'],
                    'correcta': det.get('correcta', False),
                    'opcion_elegida': det.get('opcion_elegida', ''),
                    'feedback': det.get('feedback', ''),
                    'tipo': 'inicial',  # Por defecto
                    'respondida': True
                })
            
    return detalles_completos

@app.route('/docente-panel')
@docente_required
def docente_panel():
    profesor_id = session.get('profesor_id')
    is_admin = session.get('admin_logged_in', False)
    connection = get_db_connection()
    if not connection:
        return "Error de conexión a la base de datos", 500
        
    cursor = connection.cursor()
    try:
        # Get profesor public name
        cursor.execute("SELECT nombre, whatsapp FROM profesores WHERE id_profesor = %s;", (profesor_id,))
        row_prof = cursor.fetchone()
        nombre_publico = row_prof[0] if (row_prof and row_prof[0]) else session.get('profesor_email', 'Docente')
        whatsapp = row_prof[1] if (row_prof and len(row_prof) > 1 and row_prof[1]) else ''
        session['profesor_nombre_publico'] = nombre_publico

        # 1. Obtener códigos de acceso
        if is_admin:
            cursor.execute("SELECT codigo_acceso FROM sesiones ORDER BY codigo_acceso;")
        else:
            cursor.execute("SELECT codigo_acceso FROM sesiones WHERE id_profesor = %s ORDER BY codigo_acceso;", (profesor_id,))
        codigos = [row[0] for row in cursor.fetchall()]
        
        # 2. Obtener historial de partidas de los estudiantes
        if is_admin:
            cursor.execute("""
                SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, re.id_resultado
                FROM resultados_estudiantes re
                JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                ORDER BY re.id_resultado DESC;
            """)
        else:
            cursor.execute("""
                SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, re.id_resultado
                FROM resultados_estudiantes re
                JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                WHERE s.id_profesor = %s
                ORDER BY re.id_resultado DESC;
            """, (profesor_id,))
        historial_raw = cursor.fetchall()
        
        historial = []
        for row in historial_raw:
            bloque = row[5] if row[5] is not None else 1
            detalles_raw = row[6] if row[6] is not None else []
            detalles_completos = obtener_detalles_completos(cursor, bloque, detalles_raw)
            historial.append({
                'alumno': capitalize_name(row[0]),
                'codigo': row[1],
                'puntaje': row[2],
                'correctas': row[3],
                'incorrectas': row[4],
                'bloque': bloque,
                'detalles': detalles_completos,
                'id_resultado': row[7]
            })
        # Obtener bloques dinámicos
        bloques_map = obtener_info_bloques()
        if not bloques_map:
            bloques_map = {
                1: 'Bloque 1: Residuos y Reciclaje',
                2: 'Bloque 2: Agua y Alcantarillado',
                3: 'Bloque 3: Consumo y Energía',
                4: 'Bloque 4: Liderazgo y Comunidad'
            }
        else:
            for b, title in list(bloques_map.items()):
                if not title.startswith(f"Bloque {b}:"):
                    bloques_map[b] = f"Bloque {b}: {title}"
                
        bloques_list = [{'id': b, 'titulo': t.replace(f"Bloque {b}:", "").strip()} for b, t in sorted(bloques_map.items())]
            
        return render_template('docente.html', codigos=codigos, historial=historial, nombre_publico=nombre_publico, whatsapp=whatsapp, is_admin=is_admin, bloques_map=bloques_map, bloques_list=bloques_list)
    except Exception as e:
        return f"Error en el servidor: {str(e)}", 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/docente/perfil', methods=['POST'])
@docente_required
def update_profile():
    profesor_id = session.get('profesor_id')
    data = request.json or {}
    nombre_publico = data.get('nombre_publico', '').strip()
    whatsapp = data.get('whatsapp', '').strip()
    
    if not nombre_publico:
        return jsonify({'error': 'El nombre público no puede estar vacío.'}), 400
    if not whatsapp:
        return jsonify({'error': 'El número de WhatsApp es obligatorio.'}), 400
        
    import re
    # Validate name
    name_pattern = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+( [a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+)*$'
    if not re.match(name_pattern, nombre_publico):
        return jsonify({'error': 'El nombre público no puede tener espacios iniciales/finales ni caracteres especiales.'}), 400
        
    # Validate WhatsApp (allow spaces in the middle)
    whatsapp_val = whatsapp.replace(' ', '')
    whatsapp_pattern = r'^\+573\d{9}$'
    if not re.match(whatsapp_pattern, whatsapp_val):
        return jsonify({'error': 'El número de WhatsApp debe comenzar con +57 y tener un número de 10 dígitos que comience con 3.'}), 400
        
    # Clean and format WhatsApp
    digits = re.sub(r'\D', '', whatsapp_val[3:])
    whatsapp_clean = f"+57 {digits}"
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE profesores SET nombre = %s, whatsapp = %s WHERE id_profesor = %s;", (nombre_publico, whatsapp_clean, profesor_id))
        connection.commit()
        session['profesor_nombre_publico'] = nombre_publico
        return jsonify({'success': True, 'nombre_publico': nombre_publico, 'whatsapp': whatsapp_clean}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/forgot-password-notify', methods=['POST'])
def forgot_password_notify():
    data = request.json or {}
    username = data.get('username')
    if not username or not isinstance(username, str):
        return jsonify({'success': False, 'error': 'Nombre de usuario requerido.'}), 400
    username = username.strip()

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500

    cursor = connection.cursor()
    try:
        # Check if user exists
        cursor.execute("SELECT id_profesor, nombre, whatsapp FROM profesores WHERE username = %s;", (username,))
        prof = cursor.fetchone()
        if not prof:
            return jsonify({'success': False, 'error': 'El usuario ingresado no está registrado.'}), 444

        id_profesor, nombre, whatsapp = prof
        
        # Check if a notification already exists for this teacher to prevent duplicates
        cursor.execute("SELECT 1 FROM notificaciones WHERE id_profesor = %s LIMIT 1;", (id_profesor,))
        notification_exists = cursor.fetchone()
        
        if not notification_exists:
            # Insert notification
            cursor.execute("""
                INSERT INTO notificaciones (id_profesor, nombre, whatsapp)
                VALUES (%s, %s, %s);
            """, (id_profesor, nombre, whatsapp))
            connection.commit()
            
        session['failed_attempts'] = 0 # reset attempts
        return jsonify({'success': True, 'message': 'Notificación enviada al administrador.'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/notifications', methods=['GET'])
@admin_required
def admin_get_notifications():
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, nombre, whatsapp, creado_en FROM notificaciones WHERE leido = FALSE ORDER BY creado_en DESC;")
        rows = cursor.fetchall()
        notifications = []
        for r in rows:
            notifications.append({
                'id': r[0],
                'nombre': r[1],
                'whatsapp': r[2] if r[2] else '',
                'creado_en': r[3].isoformat() if r[3] else None
            })
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/notifications/read', methods=['POST'])
@admin_required
def admin_mark_notifications_read():
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE notificaciones SET leido = TRUE WHERE leido = FALSE;")
        connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/docente/cambiar-password', methods=['POST'])
@docente_required
def cambiar_password():
    """Change teacher password. Verifies current password before updating."""
    profesor_id = session.get('profesor_id')
    data = request.json or {}
    password_actual  = (data.get('password_actual',  '') or '').strip()
    password_nuevo   = (data.get('password_nuevo',   '') or '').strip()
    password_confirm = (data.get('password_confirm', '') or '').strip()

    if not password_actual or not password_nuevo or not password_confirm:
        return jsonify({'success': False, 'error': 'Por favor completa todos los campos.'}), 400
    if len(password_nuevo) < 6:
        return jsonify({'success': False, 'error': 'La nueva contraseña debe tener al menos 6 caracteres.'}), 400
    if password_nuevo != password_confirm:
        return jsonify({'success': False, 'error': 'La nueva contraseña y su confirmación no coinciden.'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500

    cursor = connection.cursor()
    try:
        # Verify current password (stored in 'contrasena' column)
        cursor.execute(
            "SELECT id_profesor FROM profesores WHERE id_profesor = %s AND contrasena = %s;",
            (profesor_id, password_actual)
        )
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': 'La contraseña actual es incorrecta.'}), 401

        # Update password
        cursor.execute(
            "UPDATE profesores SET contrasena = %s WHERE id_profesor = %s;",
            (password_nuevo, profesor_id)
        )
        connection.commit()
        return jsonify({'success': True, 'message': '¡Contraseña actualizada correctamente!'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': f'Error en el servidor: {str(e)}'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/docente/generar-codigo', methods=['POST'])
@docente_required
def generar_codigo():
    if session.get('admin_logged_in'):
        return jsonify({'error': 'Los administradores no pueden generar códigos de acceso.'}), 403
        
    profesor_id = session.get('profesor_id')
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        max_attempts = 10
        for _ in range(max_attempts):
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            cursor.execute("SELECT 1 FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO sesiones (codigo_acceso, id_profesor) VALUES (%s, %s);", (codigo, profesor_id))
                connection.commit()
                return jsonify({'success': True, 'codigo_acceso': codigo})
        
        return jsonify({'error': 'No se pudo generar un código único en 10 intentos.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/docente/historial', methods=['GET'])
@docente_required
def api_historial():
    profesor_id = session.get('profesor_id')
    is_admin = session.get('admin_logged_in', False)
    codigo_filtro = request.args.get('codigo', '').strip()
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        if codigo_filtro:
            if is_admin:
                cursor.execute("""
                    SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, p.nombre, re.id_resultado
                    FROM resultados_estudiantes re
                    JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                    JOIN profesores p ON s.id_profesor = p.id_profesor
                    WHERE s.codigo_acceso = %s
                    ORDER BY re.id_resultado DESC;
                """, (codigo_filtro,))
            else:
                cursor.execute("""
                    SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, NULL, re.id_resultado
                    FROM resultados_estudiantes re
                    JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                    WHERE s.id_profesor = %s AND s.codigo_acceso = %s
                    ORDER BY re.id_resultado DESC;
                """, (profesor_id, codigo_filtro))
        else:
            if is_admin:
                cursor.execute("""
                    SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, p.nombre, re.id_resultado
                    FROM resultados_estudiantes re
                    JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                    JOIN profesores p ON s.id_profesor = p.id_profesor
                    ORDER BY re.id_resultado DESC;
                """)
            else:
                cursor.execute("""
                    SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles, NULL, re.id_resultado
                    FROM resultados_estudiantes re
                    JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                    WHERE s.id_profesor = %s
                    ORDER BY re.id_resultado DESC;
                """, (profesor_id,))
        historial_raw = cursor.fetchall()
        
        historial = []
        for row in historial_raw:
            bloque = row[5] if row[5] is not None else 1
            detalles_raw = row[6] if row[6] is not None else []
            detalles_completos = obtener_detalles_completos(cursor, bloque, detalles_raw)
            entry = {
                'alumno': capitalize_name(row[0]),
                'codigo': row[1],
                'puntaje': row[2],
                'correctas': row[3],
                'incorrectas': row[4],
                'bloque': bloque,
                'detalles': detalles_completos,
                'id_resultado': row[8]
            }
            if is_admin and row[7]:
                entry['profesor'] = row[7]
            historial.append(entry)
        return jsonify({'success': True, 'historial': historial})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# New endpoint: list codes with usage flag
@app.route('/api/docente/codigos', methods=['GET'])
@docente_required
def get_codigos():
    profesor_id = session.get('profesor_id')
    is_admin = session.get('admin_logged_in', False)
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # 1. Fetch codes (with teacher info for admin)
        if is_admin:
            cursor.execute("""
                SELECT s.codigo_acceso, p.nombre, p.username
                FROM sesiones s
                JOIN profesores p ON s.id_profesor = p.id_profesor
                ORDER BY s.codigo_acceso;
            """)
        else:
            cursor.execute("SELECT codigo_acceso, NULL, NULL FROM sesiones WHERE id_profesor = %s ORDER BY codigo_acceso;", (profesor_id,))
        sesiones = cursor.fetchall()
        
        # 2. Fetch blocks played for each code
        if is_admin:
            cursor.execute("""
                SELECT re.codigo_acceso, re.bloque 
                FROM resultados_estudiantes re
                JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso;
            """)
        else:
            cursor.execute("""
                SELECT re.codigo_acceso, re.bloque 
                FROM resultados_estudiantes re
                JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                WHERE s.id_profesor = %s;
            """, (profesor_id,))
        resultados = cursor.fetchall()
        
        # Map outcomes and teacher info in Python
        code_to_blocks = {}
        code_to_teacher = {}
        for code_row in sesiones:
            code_to_blocks[code_row[0]] = set()
            # nombre_publico or email as fallback
            teacher_name = code_row[1] if code_row[1] else (code_row[2] if code_row[2] else 'Docente')
            code_to_teacher[code_row[0]] = teacher_name
            
        for res_row in resultados:
            c = res_row[0]
            b = res_row[1] if res_row[1] is not None else 1
            if c in code_to_blocks:
                code_to_blocks[c].add(b)
                
        codigos = []
        for c, b_set in code_to_blocks.items():
            entry = {
                'codigo': c,
                'usado': len(b_set) > 0,
                'bloques': list(b_set)
            }
            if is_admin:
                entry['profesor'] = code_to_teacher.get(c, 'Docente')
            codigos.append(entry)
        return jsonify({'success': True, 'codigos': codigos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Endpoint: delete a code and ALL its associated results (with confirmation required from client)
@app.route('/api/docente/eliminar-codigo/<codigo>', methods=['DELETE'])
@docente_required
def eliminar_codigo(codigo):
    profesor_id = session.get('profesor_id')
    is_admin = session.get('admin_logged_in', False)
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # Verify ownership
        cursor.execute("SELECT id_profesor FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Código no encontrado.'}), 404
        if not is_admin and row[0] != profesor_id:
            return jsonify({'error': 'No autorizado a eliminar este código.'}), 403

        # Count results that will be deleted
        cursor.execute("SELECT COUNT(*) FROM resultados_estudiantes WHERE codigo_acceso = %s;", (codigo,))
        n_resultados = cursor.fetchone()[0]

        # Delete results first (FK constraint), then the code
        cursor.execute("DELETE FROM resultados_estudiantes WHERE codigo_acceso = %s;", (codigo,))
        cursor.execute("DELETE FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
        connection.commit()
        return jsonify({'success': True, 'partidas_eliminadas': n_resultados})
    except Exception as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Endpoint: delete a single student game result by student name + codigo
@app.route('/api/docente/eliminar-partida', methods=['DELETE'])
@docente_required
def eliminar_partida():
    """Delete a single student result row. Verifies the code belongs to this professor (if not admin)."""
    profesor_id = session.get('profesor_id')
    is_admin = session.get('admin_logged_in', False)
    data = request.json or {}
    codigo       = (data.get('codigo',  '') or '').strip()
    nombre_alumno= (data.get('alumno',  '') or '').strip()
    id_resultado = data.get('id_resultado')

    if not codigo:
        return jsonify({'success': False, 'error': 'Faltan datos.'}), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # Ownership check
        cursor.execute("SELECT id_profesor FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Código no encontrado.'}), 404
        if not is_admin and row[0] != profesor_id:
            return jsonify({'success': False, 'error': 'No autorizado.'}), 403

        if id_resultado:
            cursor.execute("DELETE FROM resultados_estudiantes WHERE id_resultado = %s AND codigo_acceso = %s;", (id_resultado, codigo))
        else:
            cursor.execute("DELETE FROM resultados_estudiantes WHERE codigo_acceso = %s AND nombre_alumno = %s;", (codigo, nombre_alumno))
        deleted = cursor.rowcount
        connection.commit()
        return jsonify({'success': True, 'eliminadas': deleted})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/profesores', methods=['GET'])
@admin_required
def admin_list_profesores():
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT 
                p.id_profesor, 
                p.username, 
                p.contrasena, 
                p.nombre,
                (SELECT COUNT(*) FROM sesiones s WHERE s.id_profesor = p.id_profesor) as total_codigos,
                (SELECT COUNT(*) FROM resultados_estudiantes re JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso WHERE s.id_profesor = p.id_profesor) as total_partidas,
                p.whatsapp
            FROM profesores p
            ORDER BY p.id_profesor;
        """)
        rows = cursor.fetchall()
        profesores = []
        for r in rows:
            profesores.append({
                'id_profesor': r[0],
                'username': r[1],
                'contrasena': r[2],
                'nombre': r[3],
                'total_codigos': r[4],
                'total_partidas': r[5],
                'whatsapp': r[6] if r[6] else ''
            })
        return jsonify({'success': True, 'profesores': profesores})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/profesor/<int:id_profesor>/detalles', methods=['GET'])
@admin_required
def admin_profesor_detalles(id_profesor):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # Fetch teacher details
        cursor.execute("SELECT username, nombre FROM profesores WHERE id_profesor = %s;", (id_profesor,))
        prof_row = cursor.fetchone()
        if not prof_row:
            return jsonify({'success': False, 'error': 'Docente no encontrado.'}), 404
            
        # Fetch sessions (codes)
        cursor.execute("SELECT codigo_acceso FROM sesiones WHERE id_profesor = %s ORDER BY codigo_acceso;", (id_profesor,))
        codes_rows = cursor.fetchall()
        
        codigos_list = []
        for c_row in codes_rows:
            codigo = c_row[0]
            # Fetch unique students who played this code
            cursor.execute("SELECT DISTINCT nombre_alumno FROM resultados_estudiantes WHERE codigo_acceso = %s ORDER BY nombre_alumno;", (codigo,))
            students = [capitalize_name(s[0]) for s in cursor.fetchall()]
            codigos_list.append({
                'codigo': codigo,
                'alumnos': students
            })
            
        return jsonify({
            'success': True,
            'nombre': prof_row[1],
            'username': prof_row[0],
            'codigos': codigos_list
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/eliminar-docente/<int:id_docente>', methods=['DELETE'])
@admin_required
def admin_eliminar_docente(id_docente):
    current_admin_id = session.get('profesor_id')
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # Check that we aren't trying to delete the active admin
        if id_docente == current_admin_id:
            return jsonify({'success': False, 'error': 'No puedes eliminar tu propia cuenta de administrador activa.'}), 400
            
        cursor.execute("SELECT username FROM profesores WHERE id_profesor = %s;", (id_docente,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Docente no encontrado.'}), 404
        if row[0].lower() == 'admin.goa':
            return jsonify({'success': False, 'error': 'No se permite eliminar la cuenta de administrador principal.'}), 400

        # Delete cascading:
        # 1. Fetch sessions
        cursor.execute("SELECT codigo_acceso FROM sesiones WHERE id_profesor = %s;", (id_docente,))
        codigos = [c[0] for c in cursor.fetchall()]
        
        if codigos:
            # 2. Delete results
            cursor.execute("DELETE FROM resultados_estudiantes WHERE codigo_acceso = ANY(%s);", (codigos,))
            # 3. Delete sessions
            cursor.execute("DELETE FROM sesiones WHERE id_profesor = %s;", (id_docente,))
        
        # 4. Delete professor
        cursor.execute("DELETE FROM profesores WHERE id_profesor = %s;", (id_docente,))
        
        # 5. Shift down IDs of remaining professors with higher IDs
        cursor.execute("UPDATE profesores SET id_profesor = id_profesor - 1 WHERE id_profesor > %s;", (id_docente,))
        
        # 6. Reset autoincrement sequence to prevent ID gaps when inserting next
        cursor.execute("SELECT setval(pg_get_serial_sequence('profesores', 'id_profesor'), COALESCE((SELECT MAX(id_profesor) FROM profesores), 1));")
        
        connection.commit()
        return jsonify({'success': True, 'message': 'El docente ha sido eliminado con éxito, las posiciones de los demás docentes se han ajustado, y sus códigos/partidas asociados se han transferido o eliminado.'})
    except Exception as e:
        connection.rollback()
        print(f"Error al eliminar docente: {e}")
        return jsonify({'success': False, 'error': 'Ocurrió un error al intentar eliminar el docente en la base de datos. Por favor, intente de nuevo.'}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/bloques', methods=['GET'])
@admin_required
def admin_list_bloques():
    info = obtener_info_bloques()
    list_bloques = [{'id': b, 'titulo': t.replace(f"Bloque {b}:", "").strip()} for b, t in sorted(info.items())]
    if not list_bloques:
        # Asegurar que los bloques por defecto 1, 2, 3 y 4 aparezcan si está vacío
        default_titles = {
            1: 'Residuos y Reciclaje',
            2: 'Agua y Alcantarillado',
            3: 'Consumo y Energía',
            4: 'Liderazgo y Comunidad'
        }
        for b, title in default_titles.items():
            list_bloques.append({'id': b, 'titulo': title})
            
    list_bloques.sort(key=lambda x: x['id'])
    return jsonify({'success': True, 'bloques': list_bloques})

@app.route('/api/admin/obtener-bloque/<int:bloque>', methods=['GET'])
@admin_required
def admin_obtener_bloque(bloque):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        # 1. Fetch material de estudio
        cursor.execute("SELECT contenido FROM material_estudio WHERE bloque = %s;", (bloque,))
        row_material = cursor.fetchone()
        material_content = row_material[0] if row_material else ""
        
        # Parse notes
        block_title = ""
        note1_title, note1_text = "", ""
        note2_title, note2_text = "", ""
        note3_title, note3_text = "", ""
        
        if material_content:
            lines = material_content.split('\n')
            if lines:
                block_title = lines[0].strip()
            
            idx1 = material_content.find("Nota 1")
            idx2 = material_content.find("Nota 2")
            idx3 = material_content.find("Nota 3")
            
            if idx1 != -1 and idx2 != -1 and idx3 != -1:
                nota1 = material_content[idx1:idx2].strip()
                nota2 = material_content[idx2:idx3].strip()
                nota3 = material_content[idx3:].strip()
                
                # Extract Title & Text for Nota 1
                if "(" in nota1 and ")" in nota1:
                    note1_title = nota1[nota1.find("(")+1 : nota1.find(")")]
                    note1_text = nota1[nota1.find("):")+2:].strip()
                else:
                    note1_text = nota1
                    
                if "(" in nota2 and ")" in nota2:
                    note2_title = nota2[nota2.find("(")+1 : nota2.find(")")]
                    note2_text = nota2[nota2.find("):")+2:].strip()
                else:
                    note2_text = nota2
                    
                if "(" in nota3 and ")" in nota3:
                    note3_title = nota3[nota3.find("(")+1 : nota3.find(")")]
                    note3_text = nota3[nota3.find("):")+2:].strip()
                else:
                    note3_text = nota3
        
        # 2. Fetch evaluation questions (5 questions)
        cursor.execute("""
            SELECT id_pregunta, pregunta, opcion_1, feedback_1, opcion_2, feedback_2, 
                   opcion_3, feedback_3, opcion_4, feedback_4, respuesta_correcta 
            FROM banco_preguntas 
            WHERE bloque = %s 
            ORDER BY id_pregunta;
        """, (bloque,))
        q_rows = cursor.fetchall()
        preguntas = []
        for r in q_rows:
            correct_val = r[10]
            correct_idx = "1"
            if correct_val == r[2]: correct_idx = "1"
            elif correct_val == r[4]: correct_idx = "2"
            elif correct_val == r[6]: correct_idx = "3"
            elif correct_val == r[8]: correct_idx = "4"
            
            preguntas.append({
                'id_pregunta': r[0],
                'pregunta': r[1],
                'opcion_1': r[2],
                'feedback_1': r[3],
                'opcion_2': r[4],
                'feedback_2': r[5],
                'opcion_3': r[6],
                'feedback_3': r[7],
                'opcion_4': r[8],
                'feedback_4': r[9],
                'correcta': correct_idx
            })
            
        # 3. Fetch story nudos (3 nodes)
        cursor.execute("""
            SELECT id_nodo, escena_titulo, texto_situacion, opcion_1, feedback_1, 
                   opcion_2, feedback_2, opcion_3, feedback_3, respuesta_correcta 
            FROM historia_interactiva 
            WHERE bloque = %s 
            ORDER BY id_nodo;
        """, (bloque,))
        n_rows = cursor.fetchall()
        nudos = []
        for r in n_rows:
            correct_val = r[9]
            correct_idx = "1"
            if correct_val == r[3]: correct_idx = "1"
            elif correct_val == r[5]: correct_idx = "2"
            elif correct_val == r[7]: correct_idx = "3"
            
            nudos.append({
                'id_nodo': r[0],
                'escena_titulo': r[1],
                'texto_situacion': r[2],
                'opcion_1': r[3],
                'feedback_1': r[4],
                'opcion_2': r[5],
                'feedback_2': r[6],
                'opcion_3': r[7],
                'feedback_3': r[8],
                'correcta': correct_idx
            })
            
        return jsonify({
            'success': True,
            'block_title': block_title,
            'notes': {
                'note1_title': note1_title, 'note1_text': note1_text,
                'note2_title': note2_title, 'note2_text': note2_text,
                'note3_title': note3_title, 'note3_text': note3_text,
            },
            'preguntas': preguntas,
            'nudos': nudos
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

def reindex_questions_and_nodes(cursor):
    # 1. Re-index material_estudio
    cursor.execute("SELECT id_material, bloque, contenido FROM material_estudio ORDER BY bloque, id_material;")
    materials = cursor.fetchall()
    cursor.execute("TRUNCATE TABLE material_estudio RESTART IDENTITY CASCADE;")
    for _, bloque, contenido in materials:
        cursor.execute("INSERT INTO material_estudio (bloque, contenido) VALUES (%s, %s);", (bloque, contenido))

    # 2. Re-index banco_preguntas
    cursor.execute("""
        SELECT id_pregunta, bloque, pregunta, opcion_1, feedback_1, opcion_2, feedback_2, 
               opcion_3, feedback_3, opcion_4, feedback_4, respuesta_correcta 
        FROM banco_preguntas 
        ORDER BY bloque, id_pregunta;
    """)
    questions = cursor.fetchall()
    cursor.execute("TRUNCATE TABLE banco_preguntas RESTART IDENTITY CASCADE;")
    for q in questions:
        cursor.execute("""
            INSERT INTO banco_preguntas (bloque, pregunta, opcion_1, feedback_1, opcion_2, feedback_2, 
                                        opcion_3, feedback_3, opcion_4, feedback_4, respuesta_correcta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, q[1:])
        
    # 3. Re-index historia_interactiva
    cursor.execute("""
        SELECT id_nodo, bloque, escena_titulo, texto_situacion, opcion_1, feedback_1, 
               opcion_2, feedback_2, opcion_3, feedback_3, respuesta_correcta 
        FROM historia_interactiva 
        ORDER BY bloque, id_nodo;
    """)
    nodes = cursor.fetchall()
    cursor.execute("TRUNCATE TABLE historia_interactiva RESTART IDENTITY CASCADE;")
    for n in nodes:
        cursor.execute("""
            INSERT INTO historia_interactiva (bloque, escena_titulo, texto_situacion, opcion_1, feedback_1, 
                                             opcion_2, feedback_2, opcion_3, feedback_3, respuesta_correcta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, n[1:])

@app.route('/api/admin/guardar-bloque', methods=['POST'])
@admin_required
def admin_guardar_bloque():
    data = request.json or {}
    bloque = data.get('bloque')
    block_title = data.get('block_title', '').strip()
    notes = data.get('notes', {})
    preguntas = data.get('preguntas', [])
    nudos = data.get('nudos', [])
    
    if not bloque:
        return jsonify({'success': False, 'error': 'Falta el número de bloque.'}), 400
    if not block_title:
        return jsonify({'success': False, 'error': 'El título del bloque no puede estar vacío.'}), 400
        
    # Validar Notas
    note1_title = notes.get('note1_title', '').strip()
    note1_text = notes.get('note1_text', '').strip()
    note2_title = notes.get('note2_title', '').strip()
    note2_text = notes.get('note2_text', '').strip()
    note3_title = notes.get('note3_title', '').strip()
    note3_text = notes.get('note3_text', '').strip()
    
    if not note1_title or not note1_text or not note2_title or not note2_text or not note3_title or not note3_text:
        return jsonify({'success': False, 'error': 'Todos los campos de las notas son obligatorios.'}), 400
        
    # Validar Preguntas (deben ser exactamente 5)
    if len(preguntas) != 5:
        return jsonify({'success': False, 'error': 'Se requieren exactamente 5 preguntas de evaluación.'}), 400
        
    for idx, q in enumerate(preguntas):
        pregunta = q.get('pregunta', '').strip()
        op1 = q.get('opcion_1', '').strip()
        fb1 = q.get('feedback_1', '').strip()
        op2 = q.get('opcion_2', '').strip()
        fb2 = q.get('feedback_2', '').strip()
        op3 = q.get('opcion_3', '').strip()
        fb3 = q.get('feedback_3', '').strip()
        op4 = q.get('opcion_4', '').strip()
        fb4 = q.get('feedback_4', '').strip()
        correcta = q.get('correcta', '').strip()
        
        if not pregunta or not op1 or not fb1 or not op2 or not fb2 or not op3 or not fb3 or not op4 or not fb4 or not correcta:
            return jsonify({'success': False, 'error': f'Todos los campos son obligatorios. Falta completar datos en la pregunta {idx + 1}.'}), 400
        if correcta not in ['1', '2', '3', '4']:
            return jsonify({'success': False, 'error': f'La respuesta correcta de la pregunta {idx + 1} debe ser una opción válida (1, 2, 3 o 4).'}), 400
            
    # Validar Nudos (deben ser exactamente 3)
    if len(nudos) != 3:
        return jsonify({'success': False, 'error': 'Se requieren exactamente 3 nudos para la historia interactiva.'}), 400
        
    for idx, n in enumerate(nudos):
        titulo = n.get('escena_titulo', '').strip()
        contexto = n.get('texto_situacion', '').strip()
        op1 = n.get('opcion_1', '').strip()
        fb1 = n.get('feedback_1', '').strip()
        op2 = n.get('opcion_2', '').strip()
        fb2 = n.get('feedback_2', '').strip()
        op3 = n.get('opcion_3', '').strip()
        fb3 = n.get('feedback_3', '').strip()
        correcta = n.get('correcta', '').strip()
        
        if not titulo or not contexto or not op1 or not fb1 or not op2 or not fb2 or not op3 or not fb3 or not correcta:
            return jsonify({'success': False, 'error': f'Todos los campos son obligatorios. Falta completar datos en el nudo {idx + 1} de la historia.'}), 400
        if correcta not in ['1', '2', '3']:
            return jsonify({'success': False, 'error': f'La decisión correcta del nudo {idx + 1} debe ser una opción válida (1, 2 o 3).'}), 400
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        # 1. Assemble material_estudio content string
        material_str = f"{block_title}\n\nI. Kit del Guardián\n\n"
        material_str += f"Nota 1 ({notes.get('note1_title', '').strip()}): {notes.get('note1_text', '').strip()}\n\n"
        material_str += f"Nota 2 ({notes.get('note2_title', '').strip()}): {notes.get('note2_text', '').strip()}\n\n"
        material_str += f"Nota 3 ({notes.get('note3_title', '').strip()}): {notes.get('note3_text', '').strip()}"
        
        # Upsert material_estudio
        cursor.execute("SELECT 1 FROM material_estudio WHERE bloque = %s;", (bloque,))
        if cursor.fetchone():
            cursor.execute("UPDATE material_estudio SET contenido = %s WHERE bloque = %s;", (material_str, bloque))
        else:
            cursor.execute("INSERT INTO material_estudio (bloque, contenido) VALUES (%s, %s);", (bloque, material_str))
            
        # 2. Update banco_preguntas
        cursor.execute("DELETE FROM banco_preguntas WHERE bloque = %s;", (bloque,))
        for idx, q in enumerate(preguntas):
            correct_idx = q.get('correcta', '1')
            correct_ans = q.get(f'opcion_{correct_idx}', '')
            
            cursor.execute("""
                INSERT INTO banco_preguntas (bloque, pregunta, opcion_1, feedback_1, opcion_2, feedback_2, opcion_3, feedback_3, opcion_4, feedback_4, respuesta_correcta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                bloque,
                q.get('pregunta', '').strip(),
                q.get('opcion_1', '').strip(),
                q.get('feedback_1', '').strip(),
                q.get('opcion_2', '').strip(),
                q.get('feedback_2', '').strip(),
                q.get('opcion_3', '').strip(),
                q.get('feedback_3', '').strip(),
                q.get('opcion_4', '').strip(),
                q.get('feedback_4', '').strip(),
                correct_ans.strip()
            ))
            
        # 3. Update historia_interactiva
        cursor.execute("DELETE FROM historia_interactiva WHERE bloque = %s;", (bloque,))
        for idx, n in enumerate(nudos):
            correct_idx = n.get('correcta', '1')
            correct_ans = n.get(f'opcion_{correct_idx}', '')
            
            cursor.execute("""
                INSERT INTO historia_interactiva (bloque, escena_titulo, texto_situacion, opcion_1, feedback_1, opcion_2, feedback_2, opcion_3, feedback_3, respuesta_correcta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                bloque,
                n.get('escena_titulo', '').strip(),
                n.get('texto_situacion', '').strip(),
                n.get('opcion_1', '').strip(),
                n.get('feedback_1', '').strip(),
                n.get('opcion_2', '').strip(),
                n.get('feedback_2', '').strip(),
                n.get('opcion_3', '').strip(),
                n.get('feedback_3', '').strip(),
                correct_ans.strip()
            ))
            
        # Re-index questions and nodes to make sure there are no gaps
        reindex_questions_and_nodes(cursor)
        
        connection.commit()
        return jsonify({'success': True, 'message': f'¡El contenido del Bloque {bloque} ha sido actualizado con éxito y las preguntas/historias han sido reordenadas en cascada!'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/admin/eliminar-bloque/<int:bloque>', methods=['DELETE'])
@admin_required
def admin_eliminar_bloque(bloque):
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        # Delete from material_estudio, banco_preguntas, and historia_interactiva
        cursor.execute("DELETE FROM material_estudio WHERE bloque = %s;", (bloque,))
        cursor.execute("DELETE FROM banco_preguntas WHERE bloque = %s;", (bloque,))
        cursor.execute("DELETE FROM historia_interactiva WHERE bloque = %s;", (bloque,))
        # Delete results associated with this block to keep database clean
        cursor.execute("DELETE FROM resultados_estudiantes WHERE bloque = %s;", (bloque,))
        
        # Shift down block numbers for any block > deleted block
        cursor.execute("UPDATE material_estudio SET bloque = bloque - 1 WHERE bloque > %s;", (bloque,))
        cursor.execute("UPDATE banco_preguntas SET bloque = bloque - 1 WHERE bloque > %s;", (bloque,))
        cursor.execute("UPDATE historia_interactiva SET bloque = bloque - 1 WHERE bloque > %s;", (bloque,))
        cursor.execute("UPDATE resultados_estudiantes SET bloque = bloque - 1 WHERE bloque > %s;", (bloque,))
        
        # Re-index questions and nodes to make sure there are no gaps
        reindex_questions_and_nodes(cursor)
        
        connection.commit()
        return jsonify({'success': True, 'message': f'¡El Bloque {bloque} ha sido eliminado con éxito y los números de los siguientes bloques y preguntas se han ajustado!'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/estudiante-acceso')
def estudiante_acceso():
    return render_template('estudiante_acceso.html')

@app.route('/api/estudiante/verificar-codigo', methods=['GET'])
def verificar_codigo():
    codigo = request.args.get('codigo', '').strip().upper()
    if not codigo:
        return jsonify({'success': False, 'error': 'Código vacío.'}), 400
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT p.nombre, p.username 
            FROM sesiones s 
            JOIN profesores p ON s.id_profesor = p.id_profesor 
            WHERE s.codigo_acceso = %s;
        """, (codigo,))
        row = cursor.fetchone()
        if row:
            nombre_publico = row[0] if row[0] else row[1]
            return jsonify({'success': True, 'nombre_publico': nombre_publico})
        else:
            return jsonify({'success': False, 'error': 'Código de acceso no válido o inexistente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/estudiante/datos-bloque', methods=['GET'])
def datos_bloque():
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        # Obtener dinámicamente todos los bloques que tengan preguntas cargadas
        cursor.execute("SELECT DISTINCT bloque FROM banco_preguntas;")
        bloques = [row[0] for row in cursor.fetchall()]
        if not bloques:
            bloques = [1, 2, 3, 4]  # fallback
        bloque = random.choice(bloques)
        
        # 1. Recuperar banco_preguntas (las 5 del bloque)
        cursor.execute("""
            SELECT id_pregunta, pregunta, opcion_1, feedback_1, opcion_2, feedback_2, 
                   opcion_3, feedback_3, opcion_4, feedback_4, respuesta_correcta 
            FROM banco_preguntas 
            WHERE bloque = %s
            ORDER BY id_pregunta;
        """, (bloque,))
        preguntas_rows = cursor.fetchall()
        preguntas = []
        for r in preguntas_rows:
            preguntas.append({
                'id_pregunta': r[0],
                'pregunta': r[1],
                'opcion_1': r[2],
                'feedback_1': r[3],
                'opcion_2': r[4],
                'feedback_2': r[5],
                'opcion_3': r[6],
                'feedback_3': r[7],
                'opcion_4': r[8],
                'feedback_4': r[9],
                'respuesta_correcta': r[10]
            })
            
        # 2. Recuperar historia_interactiva (los 3 nudos del bloque)
        cursor.execute("""
            SELECT id_nodo, escena_titulo, texto_situacion, opcion_1, feedback_1, 
                   opcion_2, feedback_2, opcion_3, feedback_3, respuesta_correcta 
            FROM historia_interactiva 
            WHERE bloque = %s
            ORDER BY id_nodo;
        """, (bloque,))
        nudos_rows = cursor.fetchall()
        nudos = []
        for r in nudos_rows:
            nudos.append({
                'id_nodo': r[0],
                'escena_titulo': r[1],
                'texto_situacion': r[2],
                'opcion_1': r[3],
                'feedback_1': r[4],
                'opcion_2': r[5],
                'feedback_2': r[6],
                'opcion_3': r[7],
                'feedback_3': r[8],
                'respuesta_correcta': r[9]
            })
            
        # 3. Recuperar material_estudio (las 3 notas del bloque)
        cursor.execute("""
            SELECT contenido 
            FROM material_estudio 
            WHERE bloque = %s;
        """, (bloque,))
        material_row = cursor.fetchone()
        material_content = material_row[0] if material_row else ""
        
        # Parsear las 3 notas
        idx1 = material_content.find("Nota 1")
        idx2 = material_content.find("Nota 2")
        idx3 = material_content.find("Nota 3")
        
        if idx1 != -1 and idx2 != -1 and idx3 != -1:
            nota1 = material_content[idx1:idx2].strip()
            nota2 = material_content[idx2:idx3].strip()
            nota3 = material_content[idx3:].strip()
            notas = [nota1, nota2, nota3]
        else:
            notas = [material_content]
            
        return jsonify({
            'success': True,
            'bloque': bloque,
            'preguntas': preguntas,
            'nudos': nudos,
            'notas': notas
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/estudiante/guardar-resultado', methods=['POST'])
def guardar_resultado():
    data = request.json or {}
    codigo = data.get('codigo_acceso', '').strip().upper()
    nombre = data.get('nombre_alumno', '').strip()
    puntaje = data.get('puntaje', 0)
    correctas = data.get('correctas', 0)
    incorrectas = data.get('incorrectas', 0)
    bloque = data.get('bloque', 1)
    detalles = data.get('detalles', [])
    
    if not codigo or not nombre:
        return jsonify({'success': False, 'error': 'Código o nombre del alumno faltante.'}), 400
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        detalles_json = json.dumps(detalles)
        cursor.execute("""
            INSERT INTO resultados_estudiantes (codigo_acceso, nombre_alumno, puntaje, correctas, incorrectas, bloque, detalles) 
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb);
        """, (codigo, nombre, puntaje, correctas, incorrectas, bloque, detalles_json))
        connection.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

