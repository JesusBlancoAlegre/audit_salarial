import os
from dotenv import load_dotenv
load_dotenv()

import pymysql
conn = pymysql.connect(host='localhost', user='root', password='1234', database='audit_salarial')
cursor = conn.cursor()

# Verificar si la columna ya existe
cursor.execute("SHOW COLUMNS FROM usuario LIKE 'must_change_password'")
result = cursor.fetchone()
print('Columna must_change_password existe:', result is not None)

if not result:
    # Añadir la columna
    cursor.execute("ALTER TABLE usuario ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 0")
    conn.commit()
    print('Columna must_change_password AÑADIDA correctamente')
else:
    print('No se requiere accion, la columna ya existe')

# Verificar y arreglar los usuarios
cursor.execute('SELECT id, email, activo FROM usuario')
users = cursor.fetchall()
print(f'\nTotal usuarios: {len(users)}')
for u in users:
    print(f'  ID={u[0]} email={u[1]} activo={u[2]}')

# Activar todos los usuarios con rol ADMIN que esten inactivos
cursor.execute("UPDATE usuario u JOIN rol r ON u.rol_id = r.id SET u.activo = 1 WHERE r.nombre = 'ADMIN' AND u.activo = 0")
affected = cursor.rowcount
conn.commit()
print(f'\nAdmins reactivados: {affected}')

conn.close()
print('\nListo.')
