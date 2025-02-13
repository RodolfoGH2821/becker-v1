from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
clave_plana = "hola123" 
clave_encriptada = bcrypt.generate_password_hash(clave_plana).decode('utf-8')

print("Contraseña encriptada:", clave_encriptada)
