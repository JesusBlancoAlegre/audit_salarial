import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("d:/TFG/src/.env")
engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    # Fix recomendacion_catalogo
    conn.execute(text("ALTER TABLE recomendacion_catalogo MODIFY tipo VARCHAR(30) NOT NULL DEFAULT 'OTRA';"))
    
    # Fix anomalia
    try:
        conn.execute(text("ALTER TABLE anomalia ADD COLUMN id_fila_excel INT AFTER dimension_valor;"))
    except Exception:
        pass
        
    conn.execute(text("ALTER TABLE anomalia MODIFY metodo VARCHAR(30) NOT NULL;"))
    conn.execute(text("ALTER TABLE anomalia MODIFY severidad VARCHAR(20) NOT NULL DEFAULT 'MEDIA';"))
    
    conn.commit()
print("Fixed schemas in DB")
