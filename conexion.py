import mysql.connector
from mysql.connector import Error
from flask_bcrypt import check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.connection = self.connect()
    
    
    def connect(self):
        """Establece la conexión a la base de datos"""
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv('DB_HOST'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME')
        )
            if self.connection.is_connected():
                print("✅ Conexión exitosa a la base de datos")
        except Error as e:
            print(f"❌ Error al conectar: {e}")
            self.connection = None

    def disconnect(self):
        """Cierra la conexión activa"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 Conexión cerrada")

    def execute_query(self, query, params=None):
        """Ejecuta consultas de escritura (INSERT/UPDATE/DELETE)"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()

            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
                return True
        except Error as e:
            print(f"❌ Error en execute_query: {e}")
            if self.connection:
                self.connection.rollback()
            return False

    def fetch_query(self, query, params=None):
        """Ejecuta consultas de lectura (SELECT)"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()

            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Error as e:
            print(f"Error en fetch_query: {e}")
            return None

    def verificar_usuario(self, usuario, clave):
        """Verifica si el usuario existe y valida la contraseña"""
        query = "SELECT id, usuario, clave FROM usuarios WHERE usuario = %s"
        resultado = self.fetch_query(query, (usuario,))

        if resultado:
            usuario_data = resultado[0]
            hashed_password = usuario_data["clave"]

            if hashed_password and check_password_hash(hashed_password, clave):
                print("Contraseña correcta")
                return usuario_data["id"]
            else:
                print("❌ Contraseña incorrecta")

        print("❌ Usuario o contraseña incorrectos")
        return None
