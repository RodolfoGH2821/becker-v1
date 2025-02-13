from flask import Flask, render_template, request, redirect, url_for, session, flash
from conexion import Database
import os
import shutil  # Para eliminar carpetas y archivos
from functools import wraps
from flask_bcrypt import Bcrypt
from flask_session import Session
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicialización de la aplicación Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Configuración de la sesión
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.template_filter('miles')
def miles_filter(value):
    try:
        # Convertir a entero y formatear con comas
        formateado = f"{int(value):,}"
        # Reemplazar comas por puntos
        return formateado.replace(",", ".")
    except:
        # Si falla (por ej., no es número), regresamos el valor original
        return value


# Instancia de la base de datos
db = Database()

# Decorador para proteger rutas
def login_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Debes iniciar sesión para acceder a esta página", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorador

# Context Processor para que 'session' esté disponible en todas las plantillas
@app.context_processor
def inject_session():
    return dict(session=session)

# Configuración de la carpeta para guardar imágenes (usando app.root_path)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'img')

# Crear el directorio si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

### --- RUTAS PÚBLICAS --- ###
@app.route('/')
def index():
    return render_template('home.html', active_page='index')

@app.route('/vehiculos')
def vehiculos():
    """Muestra la lista de vehículos disponibles."""
    select_query = """
        SELECT 
            v.patente, 
            v.marca, 
            v.modelo, 
            v.precio,
            v.año, 
            v.estado,
            v.descripcion,
            -- Subconsulta para obtener una imagen (si existe)
            (SELECT ruta FROM imagenes WHERE imagenes.patente = v.patente LIMIT 1) AS img
        FROM vehiculos v
    """
    autos = db.fetch_query(select_query)
    return render_template('vehiculos.html', autos=autos)


@app.route('/vehiculo/<string:patente>')
def vehiculo(patente):
    """Muestra la información de un vehículo específico."""
    query_vehiculo = "SELECT * FROM vehiculos WHERE patente = %s"
    query_imagenes = "SELECT ruta FROM imagenes WHERE patente = %s"

    vehiculo = db.fetch_query(query_vehiculo, (patente,))
    imagenes = db.fetch_query(query_imagenes, (patente,))

    if not vehiculo:
        return "Vehículo no encontrado", 404

    return render_template('vehiculo.html', vehiculo=vehiculo[0], imagenes=imagenes)

@app.route('/contacto')
def contacto():
    return render_template('contacto.html', active_page='contacto')

### --- RUTAS PROTEGIDAS --- ###
@app.route('/admin')
@login_requerido
def admin():
    """Panel de administración (requiere login)."""
    return render_template('admin.html', active_page='admin')

@app.route('/admin/agregar_vehiculo', methods=['GET', 'POST'])
@login_requerido
def guardar_vehiculo():
    """Permite agregar un vehículo al sistema."""
    if request.method == 'POST':
        patente = request.form.get('patente').strip()
        marca = request.form.get('marca').strip()
        modelo = request.form.get('modelo').strip()
        precio = request.form.get('precio').strip()
        año = request.form.get('año').strip()
        descripcion = request.form.get('descripcion').strip()
        transmicion = request.form.get('transmicion').strip()
        direccion = request.form.get('direccion').strip()
        combustible = request.form.get('combustible').strip()
        fecha_adquisicion = request.form.get('fecha_adquisicion').strip()
        estado = request.form.get('estado').strip()
        kilometraje = request.form.get('kilometraje').strip()
        imagenes = request.files.getlist('imagenes')

        if not all([patente, marca, modelo, precio, año, descripcion, transmicion, direccion, combustible,  fecha_adquisicion, estado, kilometraje ]):
            flash("Todos los campos son obligatorios.", "warning")
            return render_template('agregar_vehiculo.html')

        # Crear carpeta para el vehículo en static/img usando la patente
        carpeta = os.path.join(app.config['UPLOAD_FOLDER'], patente)
        os.makedirs(carpeta, exist_ok=True)

        try:
            query_vehiculo = """
                INSERT INTO vehiculos (patente, marca, modelo, precio, año, descripcion, transmicion, direccion, combustible, fecha_adquisicion, estado, kilometraje)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )
            """
            db.execute_query(query_vehiculo, (patente, marca, modelo, precio, año, descripcion, transmicion, direccion, combustible, fecha_adquisicion, estado, kilometraje))

            for imagen in imagenes:
                if imagen and imagen.filename:
                    # Se construye la ruta relativa para la BD y la ruta absoluta para guardar el archivo
                    ruta_relativa = os.path.join('img', patente, imagen.filename).replace('\\', '/')
                    ruta_absoluta = os.path.join(carpeta, imagen.filename)
                    imagen.save(ruta_absoluta)

                    query_imagen = "INSERT INTO imagenes (patente, ruta) VALUES (%s, %s)"
                    db.execute_query(query_imagen, (patente, ruta_relativa))

            flash("Vehículo agregado con éxito.", "success")
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f"Error al agregar el vehículo: {str(e)}", "danger")

    return render_template('agregar_vehiculo.html', active_page='agregar_vehiculo')

@app.route('/admin/eliminar_vehiculo', methods=['GET', 'POST'])
@login_requerido
def eliminar_vehiculo():
    """Permite eliminar un vehículo."""
    if request.method == 'POST':
        patente = request.form.get('patente').strip()

        if not patente:
            flash("Debe ingresar una patente.", "warning")
            return render_template('eliminar_vehiculo.html')

        query_verificar = "SELECT * FROM vehiculos WHERE patente = %s"
        vehiculo = db.fetch_query(query_verificar, (patente,))

        if not vehiculo:
            flash("El vehículo no existe.", "danger")
            return render_template('eliminar_vehiculo.html')

        try:
            query_eliminar_imagenes = "DELETE FROM imagenes WHERE patente = %s"
            query_eliminar_vehiculo = "DELETE FROM vehiculos WHERE patente = %s"
            db.execute_query(query_eliminar_imagenes, (patente,))
            db.execute_query(query_eliminar_vehiculo, (patente,))

            # Se elimina la carpeta creada para el vehículo dentro de static/img
            carpeta_vehiculo = os.path.join(app.config['UPLOAD_FOLDER'], patente)
            shutil.rmtree(carpeta_vehiculo, ignore_errors=True)

            flash("Vehículo eliminado con éxito.", "success")
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f"Error al eliminar el vehículo: {str(e)}", "danger")

    return render_template('eliminar_vehiculo.html')

### --- NUEVAS RUTAS PARA GESTIÓN DE VEHÍCULOS --- ###
@app.route('/admin/listar_vehiculos')
@login_requerido
def listar_vehiculos():
    """
    Lista los vehículos disponibles en tarjetas Bootstrap con su nombre
    y un botón para habilitar la edición.
    """
    query = """
        SELECT v.patente, v.marca, v.modelo, v.precio,
        (SELECT ruta FROM imagenes WHERE imagenes.patente = v.patente LIMIT 1) AS img
        FROM vehiculos v
    """
    vehiculos = db.fetch_query(query)
    return render_template('listar_vehiculos.html', vehiculos=vehiculos, active_page='listar_vehiculos')

@app.route('/admin/editar_vehiculo/<string:patente>', methods=['GET', 'POST'])
@login_requerido
def editar_vehiculo(patente):
    """
    Permite editar la información del vehículo y agregar nuevas imágenes.
    Se actualizan los datos en la base de datos y se guardan las imágenes
    en la carpeta 'static/img/<patente>'.
    """
    if request.method == 'POST':
        marca = request.form.get('marca', '').strip()
        modelo = request.form.get('modelo', '').strip()
        precio = request.form.get('precio', '').strip()
        año = request.form.get('año', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        nuevas_imagenes = request.files.getlist('imagenes')

        if not all([marca, modelo, precio, año, descripcion]):
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for('editar_vehiculo', patente=patente))

        try:
            query_update = """
                UPDATE vehiculos
                SET marca=%s, modelo=%s, precio=%s, año=%s, descripcion=%s
                WHERE patente=%s
            """
            db.execute_query(query_update, (marca, modelo, precio, año, descripcion, patente))

            # Crear carpeta para el vehículo si no existe
            carpeta = os.path.join(app.config['UPLOAD_FOLDER'], patente)
            os.makedirs(carpeta, exist_ok=True)

            # Guardar nuevas imágenes
            for imagen in nuevas_imagenes:
                if imagen and imagen.filename:
                    ruta_relativa = os.path.join('img', patente, imagen.filename).replace('\\', '/')
                    ruta_absoluta = os.path.join(carpeta, imagen.filename)
                    imagen.save(ruta_absoluta)

                    query_insert_imagen = "INSERT INTO imagenes (patente, ruta) VALUES (%s, %s)"
                    db.execute_query(query_insert_imagen, (patente, ruta_relativa))

            flash("Vehículo actualizado con éxito.", "success")
            return redirect(url_for('listar_vehiculos'))
        except Exception as e:
            flash(f"Error al actualizar el vehículo: {str(e)}", "danger")
            return redirect(url_for('editar_vehiculo', patente=patente))

    # GET: Obtener datos actuales del vehículo e imágenes asociadas
    query_vehiculo = "SELECT * FROM vehiculos WHERE patente = %s"
    vehiculo = db.fetch_query(query_vehiculo, (patente,))
    if not vehiculo:
        flash("Vehículo no encontrado.", "danger")
        return redirect(url_for('listar_vehiculos'))
    query_imagenes = "SELECT id, ruta FROM imagenes WHERE patente = %s"
    imagenes = db.fetch_query(query_imagenes, (patente,))
    return render_template('editar_vehiculo.html',
                           vehiculo=vehiculo[0],
                           imagenes=imagenes,
                           active_page='editar_vehiculo')

@app.route('/admin/eliminar_imagen/<int:id>', methods=['POST'])
@login_requerido
def eliminar_imagen(id):
    """
    Elimina una imagen específica del vehículo.
    Se elimina el archivo físico y se remueve el registro de la base de datos.
    """
    query_imagen = "SELECT patente, ruta FROM imagenes WHERE id = %s"
    imagen = db.fetch_query(query_imagen, (id,))
    if not imagen:
        flash("Imagen no encontrada.", "warning")
        return redirect(url_for('listar_vehiculos'))

    patente = imagen[0]['patente']
    # Usamos app.root_path para construir la ruta absoluta correcta
    ruta_imagen = os.path.join(app.root_path, 'static', imagen[0]['ruta'])
    try:
        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)
        query_delete = "DELETE FROM imagenes WHERE id = %s"
        db.execute_query(query_delete, (id,))
        flash("Imagen eliminada con éxito.", "success")
    except Exception as e:
        flash(f"Error al eliminar la imagen: {str(e)}", "danger")

    return redirect(url_for('editar_vehiculo', patente=patente))

### --- AUTENTICACIÓN --- ###
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Manejo de autenticación de usuarios."""
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('clave', '').strip()

        if not usuario or not clave:
            flash("Usuario y contraseña son obligatorios", "danger")
            return render_template('login.html')

        usuario_id = db.verificar_usuario(usuario, clave)
        if usuario_id:
            session['usuario_id'] = usuario_id
            session['usuario'] = usuario
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for('admin'))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash("Sesión cerrada correctamente", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=False)
