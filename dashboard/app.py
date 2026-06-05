from flask import Flask, jsonify, request, render_template
import psycopg2

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
