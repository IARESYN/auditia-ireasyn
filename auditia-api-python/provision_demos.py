from sqlmodel import Session, select
from database import engine
from models import Workspace, User, Empresa, Auditoria
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def provision_demos():
    with Session(engine) as session:
        # 1. Crear Demo Freemium
        demo_free = session.exec(select(Workspace).where(Workspace.name == "Demo Freemium IARESYN")).first()
        if not demo_free:
            demo_free = Workspace(
                id="ws-demo-freemium",
                name="Demo Freemium IARESYN",
                subscription_status="FREEMIUM"
            )
            session.add(demo_free)
            print("Creado Workspace Demo Freemium")
            
            # Usuario para la demo
            user_free = User(
                id="user-demo-freemium",
                email="freemium@iaresyn.ai",
                password=pwd_context.hash("demo2026"),
                first_name="Demo",
                last_name="Freemium",
                role="ADMIN",
                workspace_id=demo_free.id
            )
            session.add(user_free)
        
        # 2. Crear Demo Active
        demo_active = session.exec(select(Workspace).where(Workspace.name == "Demo Active IARESYN")).first()
        if not demo_active:
            demo_active = Workspace(
                id="ws-demo-active",
                name="Demo Active IARESYN",
                subscription_status="ACTIVE"
            )
            session.add(demo_active)
            print("Creado Workspace Demo Active")
            
            # Usuario para la demo
            user_active = User(
                id="user-demo-active",
                email="premium@iaresyn.ai",
                password=pwd_context.hash("demo2026"),
                first_name="Demo",
                last_name="Premium",
                role="ADMIN",
                workspace_id=demo_active.id
            )
            session.add(user_active)
            
        session.commit()
        print("Aprovisionamiento de Demos completado.")

if __name__ == "__main__":
    provision_demos()
