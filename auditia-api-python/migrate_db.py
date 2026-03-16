import sqlite3
import os

db_path = "auditia.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} no encontrado.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Añadir columnas a Workspace si no existen
    try:
        # Verificamos si la columna ya existe
        cursor.execute("PRAGMA table_info(workspace)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ("razon_social", "TEXT"),
            ("nif", "TEXT"),
            ("direccion_fiscal", "TEXT"),
            ("codigo_postal", "TEXT"),
            ("ciudad", "TEXT"),
            ("subscription_status", "TEXT DEFAULT 'FREEMIUM'")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Añadiendo columna {col_name} a la tabla workspace...")
                cursor.execute(f"ALTER TABLE workspace ADD COLUMN {col_name} {col_type}")
            else:
                print(f"La columna {col_name} ya existe en workspace.")
                
    except Exception as e:
        print(f"Error migrando workspace: {e}")

    # 2. Crear tabla Factura si no existe ( SQLModel create_all lo haría, pero aseguramos)
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS factura (
            id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            stripe_id TEXT,
            monto REAL NOT NULL,
            moneda TEXT DEFAULT 'EUR',
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT DEFAULT 'ALTA',
            estado TEXT DEFAULT 'PAGADA',
            pdf_url TEXT,
            FOREIGN KEY (workspace_id) REFERENCES workspace (id)
        )
        """)
        print("Tabla factura verificada/creada.")
    except Exception as e:
        print(f"Error creando tabla factura: {e}")

    conn.commit()
    conn.close()
    print("Migración completada con éxito.")

if __name__ == "__main__":
    migrate()
