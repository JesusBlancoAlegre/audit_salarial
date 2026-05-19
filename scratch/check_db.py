import os
from dotenv import load_dotenv
load_dotenv()

import pymysql
conn = pymysql.connect(host='localhost', user='root', password='1234', database='audit_salarial')
cursor = conn.cursor()

# Ver todas las tablas
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
print("Tablas en la base de datos:")
for t in tables:
    print(f"  - {t[0]}")
    cursor.execute(f"SELECT COUNT(*) FROM `{t[0]}`")
    count = cursor.fetchone()[0]
    print(f"      Registros: {count}")

conn.close()
