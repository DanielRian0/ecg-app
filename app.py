from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime
import time
import serial
from supabase import create_client, Client

app = Flask(__name__)

# Credenciales de Supabase
SUPABASE_URL = "https://arvrvecnxxtapxdhadux.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFydnJ2ZWNueHh0YXB4ZGhhZHV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE5MDA5MTUsImV4cCI6MjA0NzQ3NjkxNX0.vwFh9AnOhSTrVDYLn2k4Vxu7-e5rKi5b9RKRy1ap8cM"

# Inicializar Supabase con manejo de errores
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Error al inicializar Supabase: {str(e)}")
    supabase = None

def validate_supabase_connection():
    """Validar la conexión a Supabase"""
    if not supabase:
        raise Exception('Error de conexión con la base de datos')

@app.route('/')
def index():
    """Ruta principal que renderiza el template"""
    try:
        return render_template('index.html')
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error al cargar la página: {str(e)}"
        }), 500

@app.route('/api/pacientes', methods=['GET'])
def obtener_pacientes():
    """Obtener lista de pacientes con búsqueda opcional"""
    try:
        validate_supabase_connection()
        search = request.args.get('search', '')
        query = supabase.table('pacientes').select("*")
        
        if search:
            query = query.ilike('nombre', f'%{search}%')
        
        response = query.execute()
        
        if not hasattr(response, 'data'):
            raise Exception('Error al obtener datos de Supabase')

        # Formatear las fechas para mejor presentación
        formatted_data = []
        for paciente in response.data:
            paciente_formatted = dict(paciente)
            for fecha_campo in ['fecha_registro', 'ultima_lectura']:
                if paciente.get(fecha_campo):
                    try:
                        fecha = datetime.fromisoformat(paciente[fecha_campo])
                        paciente_formatted[fecha_campo] = fecha.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        paciente_formatted[fecha_campo] = 'Fecha inválida'
            formatted_data.append(paciente_formatted)

        return jsonify({
            'success': True,
            'data': formatted_data,
            'total': len(formatted_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener pacientes: {str(e)}'
        }), 500

@app.route('/api/pacientes', methods=['POST'])
def agregar_paciente():
    """Agregar un nuevo paciente"""
    try:
        validate_supabase_connection()
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['nombre', 'edad', 'enfermedades']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'El campo {field} es requerido')

        # Crear el nuevo paciente con los campos correctos
        nuevo_paciente = {
            'nombre': data['nombre'],
            'edad': int(data['edad']),
            'enfermedades': data['enfermedades'],
            'fecha_registro': datetime.now().isoformat(),
            # No incluimos ultima_lectura aquí, será null por defecto
        }
        
        response = supabase.table('pacientes').insert(nuevo_paciente).execute()
        
        if not response.data:
            raise Exception('Error al insertar en la base de datos')

        return jsonify({
            'success': True,
            'message': 'Paciente registrado exitosamente',
            'data': response.data[0]
        })
    except ValueError as ve:
        return jsonify({
            'success': False,
            'message': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al registrar paciente: {str(e)}'
        }), 500

@app.route('/api/pacientes/<int:id>', methods=['PUT'])
def actualizar_paciente(id):
    """Actualizar información de un paciente existente"""
    try:
        validate_supabase_connection()
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['nombre', 'edad', 'enfermedades']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'El campo {field} es requerido')

        paciente_actualizado = {
            'nombre': data['nombre'],
            'edad': int(data['edad']),
            'enfermedades': data['enfermedades']
        }
        
        response = supabase.table('pacientes').update(paciente_actualizado).eq('id', id).execute()
        
        if not response.data:
            raise Exception('Paciente no encontrado')

        return jsonify({
            'success': True,
            'message': 'Paciente actualizado exitosamente',
            'data': response.data[0]
        })
    except ValueError as ve:
        return jsonify({
            'success': False,
            'message': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al actualizar paciente: {str(e)}'
        }), 500

@app.route('/api/pacientes/<int:id>', methods=['DELETE'])
def eliminar_paciente(id):
    """Eliminar un paciente"""
    try:
        validate_supabase_connection()
        response = supabase.table('pacientes').delete().eq('id', id).execute()
        
        if not response.data:
            raise Exception('Paciente no encontrado')

        return jsonify({
            'success': True,
            'message': 'Paciente eliminado exitosamente'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al eliminar paciente: {str(e)}'
        }), 500

@app.route('/api/ecg/<int:paciente_id>', methods=['POST'])
def iniciar_ecg(paciente_id):
    """Iniciar lectura de ECG para un paciente"""
    try:
        validate_supabase_connection()
        
        def generate():
            try:
                lecturas = []
                tiempo_inicio = time.time()
                
                # Configurar puerto serial
                with serial.Serial('COM3', 115200, timeout=1) as puerto_serial:
                    for _ in range(100):  # 100 lecturas de ejemplo
                        if puerto_serial.in_waiting > 0:
                            linea = puerto_serial.readline().decode('utf-8').strip()
                            valor = float(linea)
                            
                            lectura = {
                                'paciente_id': paciente_id,
                                'lectura': valor,
                                'tiempo': time.time() - tiempo_inicio,
                                'fecha': datetime.now().isoformat()
                            }
                            lecturas.append(lectura)
                            
                            # Enviar lectura en tiempo real
                            yield f"data: {{'valor': {valor}, 'tiempo': {time.time() - tiempo_inicio}}}\n\n"
                        
                        time.sleep(0.1)
                
                # Guardar todas las lecturas en la base de datos
                if lecturas:
                    supabase.table('lecturas').insert(lecturas).execute()
                    
                    # Actualizar última lectura del paciente
                    supabase.table('pacientes').update({
                        'ultima_lectura': datetime.now().isoformat()
                    }).eq('id', paciente_id).execute()
            
            except Exception as e:
                print(f"Error durante la lectura ECG: {str(e)}")
                yield f"data: {{'error': '{str(e)}'}}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al iniciar ECG: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas generales"""
    try:
        validate_supabase_connection()
        response = supabase.table('pacientes').select("count", count='exact').execute()
        
        total_pacientes = response.count if hasattr(response, 'count') else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_pacientes': total_pacientes,
                'ultima_actualizacion': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener estadísticas: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    """Manejador de error 404"""
    return jsonify({
        'success': False,
        'message': 'Recurso no encontrado'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejador de error 500"""
    return jsonify({
        'success': False,
        'message': 'Error interno del servidor'
    }), 500

if __name__ == '__main__':
    app.run(debug=True)