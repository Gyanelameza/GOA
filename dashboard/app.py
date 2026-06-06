from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
import psycopg2
import random
import string
import json

app = Flask(__name__)
app.secret_key = 'goa_secret_key_for_session_management_2026'

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

def docente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'profesor_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado. Inicie sesión.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'profesor_id' in session:
        return redirect(url_for('docente_panel'))
        
    error = None
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            
        if not email or not password:
            error = "Por favor, llene todos los campos."
        else:
            connection = get_db_connection()
            if not connection:
                error = "No se pudo conectar a la base de datos."
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute("SELECT id_profesor, nombre, email FROM profesores WHERE email = %s AND nombre = %s;", (email, password))
                    profesor = cursor.fetchone()
                    if profesor:
                        session['profesor_id'] = profesor[0]
                        session['profesor_nombre'] = profesor[1]
                        session['profesor_email'] = profesor[2]
                        if request.is_json:
                            return jsonify({'success': True, 'redirect': url_for('docente_panel')})
                        return redirect(url_for('docente_panel'))
                    else:
                        error = "Correo o contraseña incorrectos."
                except Exception as e:
                    error = f"Error en el servidor: {str(e)}"
                finally:
                    cursor.close()
                    connection.close()
        
        if request.is_json:
            return jsonify({'success': False, 'error': error}), 401
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

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
    connection = get_db_connection()
    if not connection:
        return "Error de conexión a la base de datos", 500
        
    cursor = connection.cursor()
    try:
        # Get profesor public name
        cursor.execute("SELECT nombre_publico FROM profesores WHERE id_profesor = %s;", (profesor_id,))
        row_prof = cursor.fetchone()
        nombre_publico = row_prof[0] if (row_prof and row_prof[0]) else session.get('profesor_nombre')
        session['profesor_nombre_publico'] = nombre_publico

        # 1. Obtener códigos de acceso generados por el docente
        cursor.execute("SELECT codigo_acceso FROM sesiones WHERE id_profesor = %s ORDER BY codigo_acceso;", (profesor_id,))
        codigos = [row[0] for row in cursor.fetchall()]
        
        # 2. Obtener historial de partidas de los estudiantes para los códigos del docente
        cursor.execute("""
            SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles 
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
                'alumno': row[0],
                'codigo': row[1],
                'puntaje': row[2],
                'correctas': row[3],
                'incorrectas': row[4],
                'bloque': bloque,
                'detalles': detalles_completos
            })
            
        return render_template('docente.html', codigos=codigos, historial=historial, nombre_publico=nombre_publico)
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
    
    if not nombre_publico:
        return jsonify({'error': 'El nombre público no puede estar vacío.'}), 400
        
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        cursor.execute("UPDATE profesores SET nombre_publico = %s WHERE id_profesor = %s;", (nombre_publico, profesor_id))
        connection.commit()
        session['profesor_nombre_publico'] = nombre_publico
        return jsonify({'success': True, 'nombre_publico': nombre_publico}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/api/docente/generar-codigo', methods=['POST'])
@docente_required
def generar_codigo():
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
    codigo_filtro = request.args.get('codigo', '').strip()
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
        if codigo_filtro:
            cursor.execute("""
                SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles 
                FROM resultados_estudiantes re
                JOIN sesiones s ON re.codigo_acceso = s.codigo_acceso
                WHERE s.id_profesor = %s AND s.codigo_acceso = %s
                ORDER BY re.id_resultado DESC;
            """, (profesor_id, codigo_filtro))
        else:
            cursor.execute("""
                SELECT re.nombre_alumno, re.codigo_acceso, re.puntaje, re.correctas, re.incorrectas, re.bloque, re.detalles 
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
                'alumno': row[0],
                'codigo': row[1],
                'puntaje': row[2],
                'correctas': row[3],
                'incorrectas': row[4],
                'bloque': bloque,
                'detalles': detalles_completos
            })
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
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT s.codigo_acceso, COUNT(r.id_resultado) AS usos
            FROM sesiones s
            LEFT JOIN resultados_estudiantes r ON s.codigo_acceso = r.codigo_acceso
            WHERE s.id_profesor = %s
            GROUP BY s.codigo_acceso
            ORDER BY s.codigo_acceso;
            """,
            (profesor_id,)
        )
        rows = cursor.fetchall()
        codigos = [{'codigo': row[0], 'usado': row[1] > 0} for row in rows]
        return jsonify({'success': True, 'codigos': codigos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# New endpoint: delete an unused code
@app.route('/api/docente/eliminar-codigo/<codigo>', methods=['DELETE'])
@docente_required
def eliminar_codigo(codigo):
    profesor_id = session.get('profesor_id')
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'No se pudo conectar a la base de datos.'}), 500
    cursor = connection.cursor()
    try:
        # Verify the code belongs to this professor
        cursor.execute("SELECT id_profesor FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Código no encontrado.'}), 404
        if row[0] != profesor_id:
            return jsonify({'error': 'No autorizado a eliminar este código.'}), 403
        # Check if code has any associated results
        cursor.execute("SELECT COUNT(*) FROM resultados_estudiantes WHERE codigo_acceso = %s;", (codigo,))
        usos = cursor.fetchone()[0]
        if usos > 0:
            return jsonify({'error': 'Código ya utilizado, no se puede eliminar.'}), 400
        # Delete the code
        cursor.execute("DELETE FROM sesiones WHERE codigo_acceso = %s;", (codigo,))
        connection.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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
            SELECT p.nombre_publico, p.nombre 
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
    # Elige un bloque aleatorio entre 1 y 4
    bloque = random.randint(1, 4)
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'success': False, 'error': 'No se pudo conectar a la base de datos.'}), 500
        
    cursor = connection.cursor()
    try:
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

