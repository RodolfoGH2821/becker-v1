from conexion import Database

def verificar_conexion():
    # Instanciar la clase Database con los parámetros de conexión
    db = Database(host="localhost", user="root", password="", database="becker")
    
    # Intentar conectar
    db.connect()
    
    # Verificar si la conexión fue exitosa
    if db.connection and db.connection.is_connected():
        print("La conexión a la base de datos es correcta.")
    else:
        print("Error al conectar a la base de datos.")
    
    # Cerrar la conexión después de la verificación
    db.disconnect()

if __name__ == "__main__":
    verificar_conexion()
