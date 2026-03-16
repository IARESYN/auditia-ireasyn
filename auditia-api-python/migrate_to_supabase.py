import sqlite3
import os
import json
from datetime import datetime
from sqlmodel import Session, create_engine, select, SQLModel
from models import Workspace, User, Empresa, Auditoria, Hallazgo, Documento, Factura, KnowledgeItem
from dotenv import load_dotenv

load_dotenv()

# Configuración
SQLITE_DB = "auditia.db"
# La URL de Supabase debe estar en el .env como DATABASE_URL
CLOUD_DATABASE_URL = os.getenv("DATABASE_URL")

if not CLOUD_DATABASE_URL:
    print("❌ ERROR: No se ha encontrado DATABASE_URL en el archivo .env")
    print("Configura el .env con la URI de Supabase antes de continuar.")
    exit(1)

# Asegurar formato postgresql://
if CLOUD_DATABASE_URL.startswith("postgres://"):
    CLOUD_DATABASE_URL = CLOUD_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Motores
sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB}")
cloud_engine = create_engine(CLOUD_DATABASE_URL)

def migrate():
    print("🚀 Iniciando migración de datos local -> Supabase...")
    
    # 1. Crear tablas en la nube (por seguridad)
    print("📦 Creando tablas en Supabase (si no existen)...")
    SQLModel.metadata.create_all(cloud_engine)

    with Session(sqlite_engine) as local_session:
        with Session(cloud_engine) as cloud_session:
            
            # Orden de migración por dependencias
            
            # 1. Workspaces
            print("- Migrando Workspaces...")
            workspaces = local_session.exec(select(Workspace)).all()
            for ws in workspaces:
                cloud_session.merge(ws)
            cloud_session.commit()

            # 2. Usuarios
            print("- Migrando Usuarios...")
            users = local_session.exec(select(User)).all()
            for u in users:
                cloud_session.merge(u)
            cloud_session.commit()

            # 3. Empresas
            print("- Migrando Empresas...")
            empresas = local_session.exec(select(Empresa)).all()
            for emp in empresas:
                cloud_session.merge(emp)
            cloud_session.commit()

            # 4. Auditorías
            print("- Migrando Auditorías...")
            auditorias = local_session.exec(select(Auditoria)).all()
            for aud in auditorias:
                cloud_session.merge(aud)
            cloud_session.commit()

            # 5. Hallazgos
            print("- Migrando Hallazgos...")
            hallazgos = local_session.exec(select(Hallazgo)).all()
            for h in hallazgos:
                cloud_session.merge(h)
            cloud_session.commit()

            # 6. Documentos
            print("- Migrando Documentos...")
            documentos = local_session.exec(select(Documento)).all()
            for d in documentos:
                cloud_session.merge(d)
            cloud_session.commit()

            # 7. Facturas
            print("- Migrando Facturas...")
            facturas = local_session.exec(select(Factura)).all()
            for f in facturas:
                cloud_session.merge(f)
            cloud_session.commit()

            # 8. Knowledge Items
            print("- Migrando Biblioteca Maestra...")
            knowledge = local_session.exec(select(KnowledgeItem)).all()
            for k in knowledge:
                cloud_session.merge(k)
            cloud_session.commit()

    print("✅ ¡MIGRACIÓN COMPLETADA CON ÉXITO!")
    print("Todos tus datos locales están ahora en Supabase.")

if __name__ == "__main__":
    migrate()
