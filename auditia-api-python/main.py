from fastapi import FastAPI, Depends, HTTPException, Query, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, func
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import requests
from jose import JWTError, jwt
from passlib.context import CryptContext
import traceback
import uuid
import json
import io
import os
# Removidos firebase_admin y auth directo para usar verificación manual robusta
from email_service import EmailService
from stripe_service import StripeService

# Force Project ID for Firebase Admin verification
os.environ["GOOGLE_CLOUD_PROJECT"] = "iaresyn-auditia"

try:
    import fitz  # PyMuPDF
    import docx
except ImportError:
    fitz = None
    docx = None

from database import engine, get_session, init_db
from models import Workspace, Empresa, Auditoria, Hallazgo, Documento, User, Factura, KnowledgeItem

# Firebase Configuration
FIREBASE_PROJECT_ID = "iaresyn-auditia"
GOOGLE_PUBLIC_KEYS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

class FirebaseTokenVerifier:
    """Manually verifies Firebase ID Tokens using Google's public keys."""
    _cached_keys = {}
    _last_fetch = 0

    @classmethod
    def get_public_keys(cls):
        now = datetime.utcnow().timestamp()
        # Refresh keys every hour
        if not cls._cached_keys or (now - cls._last_fetch) > 3600:
            try:
                response = requests.get(GOOGLE_PUBLIC_KEYS_URL)
                cls._cached_keys = response.json()
                cls._last_fetch = now
                print("DEBUG AUTH: Google Public Keys refreshed.")
            except Exception as e:
                print(f"DEBUG AUTH: Error fetching Google keys: {e}")
        return cls._cached_keys

    @classmethod
    def verify(cls, token: str):
        try:
            # First, decode header to get kid (key id)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not kid:
                raise Exception("Missing 'kid' in token header")

            public_keys = cls.get_public_keys()
            certificate = public_keys.get(kid)
            if not certificate:
                raise Exception(f"No match found for kid: {kid}")

            # Verify with Google's public cert
            decoded_token = jwt.decode(
                token,
                certificate,
                algorithms=["RS256"],
                audience=FIREBASE_PROJECT_ID,
                issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
            )
            return decoded_token
        except Exception as e:
            print(f"DEBUG AUTH: Manual Verification Failed: {str(e)}")
            return None

# Security
SECRET_KEY = "secret_laboral_auditia_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="Auditia API (Python)")

# --- UNIVERSAL CORS MIDDLEWARE (V4 - NUCLEAR) ---
# Solución de bajo nivel para garantizar headers en Cloud Run
@app.middleware("http")
async def universal_cors_middleware(request: Request, call_next):
    # Log Origin mirroring logic
    origin = request.headers.get("origin")
    
    # 1. Handle Preflight (OPTIONS)
    if request.method == "OPTIONS":
        response = Response(status_code=204)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-Firebase-Id-Token"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # 2. Process Actual Request
    try:
        response = await call_next(request)
    except Exception as e:
        print(f"DEBUG CORS: Server Error intercepted: {str(e)}")
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )

    # 3. Inject CORS Headers in every response (success or error)
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-Firebase-Id-Token"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response

# Global Exception Handler (CORS already handled by middleware above)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"CRITICAL ERROR: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)}
    )

# Utils
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try Firebase Verification First (Manual RS256 Check)
    try:
        token_preview = token[:20] + "..." if len(token) > 20 else token
        print(f"DEBUG AUTH: Received Token: {token_preview}")
        
        # Local JWT (HS256) Check
        if token.startswith("eyJhbGciOiJIUzI1NiIs"):
            print("DEBUG AUTH: Detected Local HS256 Token.")
            # Fallback a decodificación local más abajo
        else:
            print("DEBUG AUTH: Attempting Manual Firebase Verification...")
            decoded_token = FirebaseTokenVerifier.verify(token)
            
            if decoded_token:
                email = decoded_token.get("email")
                print(f"DEBUG AUTH: Manual Token Verification SUCCESS for: {email}")
                
                # Check user in local SQLite
                user = session.exec(select(User).where(User.email == email)).first()
                if user:
                    # Sync role if it's a superadmin email
                    is_master_email = email in ["info@iaresyn.com", "superadmin@iaresyn.com"]
                    if is_master_email and user.role != "SUPERADMIN":
                        user.role = "SUPERADMIN"
                        session.add(user)
                        session.commit()
                    return user
                else:
                    print(f"DEBUG AUTH: User {email} verified by Firebase but MISSING in local SQLite.")
            else:
                print("DEBUG AUTH: Manual Firebase Verification Failed.")
            
    except Exception as fe:
        print(f"DEBUG AUTH: Global Auth Error: {str(fe)}")
        # Fallback to local JWT if Firebase failed
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is not None:
                user = session.get(User, user_id)
                if user:
                    return user
        except JWTError:
            pass

    raise credentials_exception

async def get_superadmin(user: User = Depends(get_current_user)):
    # Platform owner bypass (info@iaresyn.com)
    if user.role != "SUPERADMIN" and user.email != "info@iaresyn.com":
        raise HTTPException(status_code=403, detail="Acceso restringido a SuperAdministradores")
    return user

@app.on_event("startup")
def on_startup():
    print("Initializing Database...")
    init_db()
    print("Database Initialized.")
    
    # Ensure superadmin exists (Auto-create if not present)
    with Session(engine) as session:
        admin_email = "info@iaresyn.com"
        existing = session.exec(select(User).where(User.email == admin_email)).first()
        if not existing:
            print("Creating default SuperAdmin...")
            ws = Workspace(name="IARESYN SYSTEM")
            session.add(ws)
            session.commit()
            session.refresh(ws)
            
            pwd = pwd_context.hash("IARESYN2026")
            admin = User(
                email=admin_email,
                password=pwd,
                first_name="SuperAdmin",
                role="SUPERADMIN",
                workspace_id=ws.id
            )
            session.add(admin)
            session.commit()
            print(f"SuperAdmin created: {admin_email} / IARESYN2026")
        else:
            # Force SuperAdmin role AND password sync
            print(f"Syncing SuperAdmin credentials for {admin_email}...")
            existing.role = "SUPERADMIN"
            pwd = pwd_context.hash("IARESYN2026")
            existing.password = pwd
            session.add(existing)
            session.commit()
            print(f"User {admin_email} synced and promoted via startup")

        # --- FALLBACK MASTER USER ---
        fallback_email = "superadmin@iaresyn.com"
        exists_fallback = session.exec(select(User).where(User.email == fallback_email)).first()
        if not exists_fallback:
            print("Creating Fallback SuperAdmin...")
            ws_sys = session.exec(select(Workspace).where(Workspace.name == "IARESYN SYSTEM")).first()
            if not ws_sys:
                ws_sys = Workspace(name="IARESYN SYSTEM")
                session.add(ws_sys)
                session.commit()
                session.refresh(ws_sys)
            
            p_master = pwd_context.hash("IARESYN2026")
            fallback = User(
                email=fallback_email,
                password=p_master,
                first_name="Master",
                role="SUPERADMIN",
                workspace_id=ws_sys.id
            )
            session.add(fallback)
            session.commit()
            print(f"Fallback SuperAdmin created: {fallback_email} / IARESYN2026")
        else:
            exists_fallback.role = "SUPERADMIN"
            exists_fallback.password = pwd_context.hash("IARESYN2026")
            session.add(exists_fallback)
            session.commit()
            print(f"Fallback SuperAdmin {fallback_email} synced.")
            
        # --- MIGRATION: Sequential Audit Codes ---
        audits_without_code = session.exec(select(Auditoria).where(Auditoria.codigo == None)).all()
        if audits_without_code:
            print(f"Found {len(audits_without_code)} audits without code. Migrating...")
            # For simplicity, we process them by workspace
            all_workspaces = session.exec(select(Workspace)).all()
            for ws in all_workspaces:
                ws_audits = session.exec(
                    select(Auditoria).join(Empresa).where(Empresa.workspace_id == ws.id).order_by(Auditoria.created_at)
                ).all()
                for i, audit in enumerate(ws_audits):
                    if not audit.codigo:
                        audit.codigo = f"AUD-{(i+1):04d}"
                        session.add(audit)
            session.commit()
            print("Audit code migration completed.")

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "FastAPI (Python)"}

# --- ADMIN (Platform Level) ---

@app.get("/api/admin/workspaces", response_model=List[Workspace])
def admin_get_workspaces(
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    return session.exec(select(Workspace)).all()

@app.post("/api/admin/provision")
def admin_provision_client(
    data: dict,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    ws_name = data.get("workspaceName")
    email = data.get("email")
    first_name = data.get("firstName")
    temp_password = data.get("tempPassword") or str(uuid.uuid4())[:8]

    if not ws_name or not email or not first_name:
        raise HTTPException(status_code=400, detail="Faltan datos obligatorios")

    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="Este email ya está registrado")

    try:
        # 1. Create Workspace
        workspace = Workspace(
            name=ws_name, 
            settings={"status": "Active"}
        )
        session.add(workspace)
        session.flush() # Generate ID without committing

        # 2. Create Admin User
        hashed_password = pwd_context.hash(temp_password)
        new_admin = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            role="ADMIN",
            workspace_id=workspace.id
        )
        session.add(new_admin)
        
        # 3. Final Commit
        session.commit()
        session.refresh(workspace)
        
        # Enviar email de bienvenida al nuevo cliente (ADMIN del workspace)
        try:
            EmailService.send_welcome_email(email, first_name, temp_password)
            print(f"DEBUG EMAIL: Welcome email sent (Provision) to {email}")
        except Exception as email_err:
            print(f"DEBUG EMAIL ERROR (Provision): {str(email_err)}")

        return {
            "status": "success",
            "workspace": workspace,
            "admin": {
                "email": email,
                "tempPassword": temp_password
            }
        }
    except Exception as e:
        session.rollback()
        print(f"PROVISIONING ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fallo en aprovisionamiento: {str(e)}")

@app.get("/api/admin/workspaces/{workspace_id}/users", response_model=List[User])
def admin_get_workspace_users(
    workspace_id: str,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    return session.exec(select(User).where(User.workspace_id == workspace_id)).all()

@app.post("/api/admin/workspaces/{workspace_id}/users")
def admin_add_user_to_workspace(
    workspace_id: str,
    data: dict,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "ADMIN") # Default to ADMIN as requested for extra admins
    first_name = data.get("firstName", "Nuevo Usuario")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña son obligatorios")
        
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=400, detail="El email ya está en uso")
        
    new_user = User(
        email=email,
        password=pwd_context.hash(password),
        first_name=first_name,
        role=role,
        workspace_id=workspace_id
    )
    session.add(new_user)
    session.commit()
    return {"status": "success", "message": f"Usuario {email} creado en el workspace"}

@app.patch("/api/admin/users/{user_id}/password")
def admin_change_user_password(
    user_id: str,
    data: dict,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    new_password = data.get("newPassword")
    if not new_password:
        raise HTTPException(status_code=400, detail="Nueva contraseña no proporcionada")
        
    target_user.password = pwd_context.hash(new_password)
    target_user.updated_at = datetime.utcnow()
    session.add(target_user)
    session.commit()
    return {"status": "success", "message": f"Contraseña de {target_user.email} actualizada"}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: str,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if target_user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes borrarte a ti mismo")
        
    session.delete(target_user)
    session.commit()
    return {"status": "success", "message": "Usuario eliminado"}

@app.put("/api/admin/workspaces/{workspace_id}/status")
def admin_update_workspace_status(
    workspace_id: str,
    data: dict,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    ws = session.get(Workspace, workspace_id)
    if not ws: raise HTTPException(status_code=404)
    
    new_status = data.get("status")
    if new_status:
        settings = ws.settings.copy() if ws.settings else {}
        settings["status"] = new_status
        ws.settings = settings
        session.add(ws)
        session.commit()
    return ws

@app.post("/api/admin/workspaces/{workspace_id}/reset-password")
def admin_reset_client_password(
    workspace_id: str,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    # Encontrar el admin principal (el primero creado)
    client_admin = session.exec(select(User).where(User.workspace_id == workspace_id, User.role == "ADMIN")).first()
    if not client_admin:
        raise HTTPException(status_code=404, detail="Admin no encontrado para este workspace")
    
    temp_password = str(uuid.uuid4())[:8]
    client_admin.password = pwd_context.hash(temp_password)
    session.add(client_admin)
    session.commit()
    
    return {"email": client_admin.email, "tempPassword": temp_password}

@app.delete("/api/admin/workspaces/{workspace_id}")
def admin_delete_workspace(
    workspace_id: str,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    ws = session.get(Workspace, workspace_id)
    if not ws: raise HTTPException(status_code=404, detail="Workspace no encontrado")
    
    # Safety Check: Can't delete the platform's root workspace
    if workspace_id == admin.workspace_id:
        raise HTTPException(status_code=400, detail="No puedes borrar tu propio entorno de sistema")

    try:
        # 1. DELETE Cascade (Flat & Robust logic)
        # -------------------------------------
        
        # Step A: Delete all Documents linked to ANY empresa in this workspace
        empresas = session.exec(select(Empresa).where(Empresa.workspace_id == workspace_id)).all()
        empresa_ids = [e.id for e in empresas]
        
        for e_id in empresa_ids:
            docs = session.exec(select(Documento).where(Documento.empresa_id == e_id)).all()
            for d in docs: session.delete(d)
        
        # Step B: Delete Findings linked to audits in this workspace
        audits = session.exec(select(Auditoria).join(Empresa).where(Empresa.workspace_id == workspace_id)).all()
        for audit in audits:
            hallazgos = session.exec(select(Hallazgo).where(Hallazgo.auditoria_id == audit.id)).all()
            for h in hallazgos: session.delete(h)
            session.delete(audit)
            
        # Step C: Delete Empresas
        for emp in empresas: session.delete(emp)

        # 2. Delete Users
        users = session.exec(select(User).where(User.workspace_id == workspace_id)).all()
        for u in users:
            if u.id != admin.id: # Never delete self
                session.delete(u)
        
        # 3. Finally delete workspace
        ws_name = ws.name
        session.delete(ws)
        session.commit()
        return {"status": "success", "message": f"Workspace '{ws_name}' y todos sus datos eliminados."}
        
    except Exception as e:
        session.rollback()
        print(f"FATAL DELETE ERROR for {workspace_id}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar el cliente por completo: {str(e)}")

# --- AUTH ---
@app.post("/api/auth/register")
def register(data: dict, session: Session = Depends(get_session)):
    print(f"Registering user: {data.get('email')}")
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    workspace_name = data.get("workspaceName") or f"Empresa de {name}"

    print(f"DEBUG: Registering user: {email}")
    print(f"DEBUG: Password type: {type(password)}")
    print(f"DEBUG: Password length: {len(password) if password else 'N/A'}")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    # Bcrypt limit check (72 bytes)
    encoded_pw = password.encode('utf-8')
    print(f"DEBUG: Encoded length: {len(encoded_pw)}")
    if len(encoded_pw) > 71:
        print(f"Validation Error: Password too long for {email}")
        raise HTTPException(status_code=400, detail="Contraseña demasiado larga (máximo 71 caracteres)")

    if session.exec(select(User).where(User.email == email)).first():
        print(f"User already exists: {email}")
        raise HTTPException(status_code=400, detail="User already exists")

    try:
        # Transactional create
        workspace = Workspace(name=workspace_name)
        session.add(workspace)
        session.commit()
        session.refresh(workspace)

        print(f"DEBUG: Workspace created: {workspace.id}")

        try:
            print("DEBUG: Attempting hash version V3...")
            hashed_password = pwd_context.hash(password)
            print("DEBUG: Hash successful V3.")
        except Exception as e:
            print(f"DEBUG: HASHING FAILED V3 - Type: {type(e)}, Msg: {str(e)}")
            raise HTTPException(status_code=400, detail=f"ERROR BETA (V3): HASH FALLIDO -> {str(e)}")

        user = User(
            email=email,
            password=hashed_password,
            first_name=name,
            workspace_id=workspace.id
        )
        session.add(user)
        session.commit()
        print(f"Successfully registered user: {email}")
        
        # Enviar email de bienvenida al usuario registrado
        try:
            EmailService.send_welcome_email(email, name)
            print(f"DEBUG EMAIL: Welcome email sent (Register) to {email}")
        except Exception as email_err:
            print(f"DEBUG EMAIL ERROR (Register): {str(email_err)}")
            
        return {"message": "Success"}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        print(f"Unexpected error during registration: {str(e)}")
        traceback.print_exc()
        session.rollback()
        raise e

@app.post("/api/auth/login")
def login(data: dict, session: Session = Depends(get_session)):
    email = data.get("email")
    password = data.get("password")

    user = session.exec(select(User).where(User.email == email)).first()
    
    # Bcrypt limit check
    if password and len(password.encode('utf-8')) > 71:
        raise HTTPException(status_code=401, detail="Credenciales inválidas (contraseña demasiado larga)")

    try:
        is_valid = user and pwd_context.verify(password, user.password)
    except ValueError:
        is_valid = False

    if not user or not is_valid:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = create_access_token(data={"sub": user.id, "workspace_id": user.workspace_id})
    
    return {
        "token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.first_name,
            "role": user.role,
            "workspace": user.workspace
        }
    }

@app.put("/api/users/me/password")
def change_password(
    data: dict,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Desactivado para clientes para centralizar gestión en SuperAdmin
    if user.role != "SUPERADMIN" and user.email != "info@iaresyn.com":
        raise HTTPException(
            status_code=403, 
            detail="La gestión de contraseñas es centralizada. Por favor, contacte con el Administrador de la Plataforma."
        )
        
    old_password = data.get("oldPassword")
    new_password = data.get("newPassword")

    if not pwd_context.verify(old_password, user.password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    
    user.password = pwd_context.hash(new_password)
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    return {"status": "success", "message": "Contraseña actualizada"}

# --- WORKSPACES ---
@app.get("/api/workspaces", response_model=List[Workspace])
def get_workspaces(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # SuperAdmin sees all, Users see only their own
    if user.role == "SUPERADMIN" or user.email == "info@iaresyn.com":
        return session.exec(select(Workspace)).all()
    return session.exec(select(Workspace).where(Workspace.id == user.workspace_id)).all()

# --- KNOWLEDGE (MASTER LIBRARY) ---
@app.get("/api/knowledge/master", response_model=List[KnowledgeItem])
def get_master_knowledge(
    session: Session = Depends(get_session)
):
    """Public endpoint for clients to sync their Master Library."""
    return session.exec(select(KnowledgeItem).where(KnowledgeItem.is_global == True)).all()

@app.post("/api/admin/knowledge/master")
def admin_save_master_knowledge(
    data: dict,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    """SuperAdmin saves a new or updated normative item to the Master Library."""
    # Filtrar campos que no pertenecen al modelo KnowledgeItem (ej: lastUpdate, type de Firestore)
    allowed_fields = {"id", "category", "title", "code", "summary", "articles", "url"}
    filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    item_id = filtered_data.get("id")
    if item_id:
        db_item = session.get(KnowledgeItem, item_id)
        if not db_item:
            db_item = KnowledgeItem()
            # Asignar campos manualmente del diccionario filtrado
            for key, value in filtered_data.items():
                setattr(db_item, key, value)
            db_item.is_global = True
        else:
            for key, value in filtered_data.items():
                setattr(db_item, key, value)
            db_item.is_global = True
            db_item.updated_at = datetime.utcnow()
    else:
        db_item = KnowledgeItem()
        for key, value in filtered_data.items():
            setattr(db_item, key, value)
        db_item.is_global = True
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@app.delete("/api/admin/knowledge/master/{item_id}")
def admin_delete_master_knowledge(
    item_id: str,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    db_item = session.get(KnowledgeItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    session.delete(db_item)
    session.commit()
    return {"status": "success"}
    return session.exec(select(Workspace).where(Workspace.id == user.workspace_id)).all()

# --- EMPRESAS ---
@app.get("/api/empresas", response_model=List[Empresa])
def get_empresas(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return session.exec(select(Empresa).where(Empresa.workspace_id == user.workspace_id)).all()

@app.post("/api/empresas", response_model=Empresa)
def create_empresa(
    empresa: Empresa, 
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    empresa.workspace_id = user.workspace_id
    session.add(empresa)
    session.commit()
    session.refresh(empresa)
    return empresa

# --- AUDITORIAS ---
@app.get("/api/auditorias", response_model=List[Auditoria])
def get_auditorias(
    empresa_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Auditoria).join(Empresa).where(Empresa.workspace_id == user.workspace_id)
    if empresa_id:
        statement = statement.where(Auditoria.empresa_id == empresa_id)
    return session.exec(statement).all()

@app.get("/api/auditorias/{audit_id}", response_model=Auditoria)
def get_auditoria(
    audit_id: str, 
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Auditoria).join(Empresa).where(
        Auditoria.id == audit_id,
        Empresa.workspace_id == user.workspace_id
    )
    audit = session.exec(statement).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit

@app.post("/api/auditorias", response_model=Auditoria)
def create_auditoria(
    auditoria: Auditoria, 
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # --- NUMERACIÓN CORRELATIVA ---
    # Contar auditorías existentes del Workspace del usuario
    statement = select(func.count(Auditoria.id)).join(Empresa).where(Empresa.workspace_id == user.workspace_id)
    count = session.exec(statement).one_or_none() or 0
    auditoria.codigo = f"AUD-{(count + 1):04d}"

    # --- FREEMIUM LOCK ---
    workspace = session.get(Workspace, user.workspace_id)
    if workspace and workspace.subscription_status == "FREEMIUM":
        # Check if they already have audits (limit to 1 or 0 for new ones)
        existing_audits = session.exec(select(Auditoria).join(Empresa).where(Empresa.workspace_id == user.workspace_id)).all()
        if len(existing_audits) >= 1:
            raise HTTPException(
                status_code=402, 
                detail="Has alcanzado el límite de auditorías de tu plan Freemium. Actualiza al Plan de Alta para crear auditorías ilimitadas."
            )

    # Verify empresa belongs to workspace
    empresa = session.get(Empresa, auditoria.empresa_id)
    if not empresa or empresa.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Forbidden")
        
    session.add(auditoria)
    session.commit()
    session.refresh(auditoria)
    return auditoria

@app.patch("/api/auditorias/{audit_id}", response_model=Auditoria)
def update_auditoria(
    audit_id: str, 
    data: dict, 
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Auditoria).join(Empresa).where(
        Auditoria.id == audit_id,
        Empresa.workspace_id == user.workspace_id
    )
    audit = session.exec(statement).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    for key, value in data.items():
        setattr(audit, key, value)
    
    session.add(audit)
    session.commit()
    session.refresh(audit)
    return audit

# --- AI DOCUMENT ANALYSIS ---
@app.post("/api/ai/analyze-document")
async def analyze_document(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # --- FREEMIUM LOCK ---
    workspace = session.get(Workspace, user.workspace_id)
    if workspace and workspace.subscription_status == "FREEMIUM":
        raise HTTPException(
            status_code=402, 
            detail="La subida y análisis de documentos por IA es una función exclusiva del Plan Alta. ¡Actualiza para empezar a auditar de verdad!"
        )

    form = await request.form()
    file = form.get("file")
    context = form.get("context", "general") # payroll, tc1, tc2, time_record, vida_laboral
    
    if not file:
        raise HTTPException(status_code=400, detail="Archivo no proporcionado")
    
    filename = file.filename.lower()
    print(f"DEBUG AI: Analyzing {filename} with context {context}")
    
    # Mock AI Reasoning Logic based on filename and context
    # In a real environment, this would call a Vision/OCR model
    findings = []
    data_extracted = {}
    
    if "payroll" in context or "nomina" in filename:
        data_extracted = {
            "employee_name": "Juan Pérez",
            "period": "Diciembre 2025",
            "base_salary": 1200,
            "irpf_percentage": 2, # Suspiciously low
            "ss_contribution": 76.50
        }
        if data_extracted["irpf_percentage"] < 8:
            findings.append({
                "id": f"ai-irpf-{uuid.uuid4().hex[:6]}",
                "area": "💰 Retribuciones",
                "severity": "GRAVE",
                "title": f"IRPF posiblemente insuficiente: {data_extracted['employee_name']}",
                "description": f"Se ha detectado una retención del {data_extracted['irpf_percentage']}% en la nómina. Para el salario base indicado, la retención mínima estimada debería ser superior al 10%.",
                "recommendation": "Verificar el modelo 145 y ajustar el porcentaje de retención para evitar sanciones de Hacienda."
            })
    
    elif "tc1" in context or "tc2" in context:
        data_extracted = {
            "company_name_match": True,
            "total_employees": 12,
            "debt_detected": False
        }
    
    elif "vida_laboral" in context:
        data_extracted = {
            "headcount": 10,
            "active_contracts": 10
        }
        # Comparison logic would happen here vs Step 2 data
        
    elif "time" in context or "jornada" in filename:
        data_extracted = {
            "total_hours_week": 42,
            "signatures_present": "partial"
        }
        if data_extracted["total_hours_week"] > 40:
            findings.append({
                "id": f"ai-hours-{uuid.uuid4().hex[:6]}",
                "area": "⏰ Jornada",
                "severity": "MUY_GRAVE",
                "title": "Exceso de jornada semanal detectado por IA",
                "description": f"Tras analizar las muestras de registro de jornada, se detectan semanas con {data_extracted['total_hours_week']}h sin compensación visible.",
                "recommendation": "Ajustar cuadrantes o compensar exceso de horas según convenio."
            })

    return {
        "status": "success",
        "filename": filename,
        "context": context,
        "data": data_extracted,
        "findings": findings,
        "ai_confidence": 0.89
    }

# --- AGENT CHAT ---
@app.post("/api/agents/chat")
async def agents_chat(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    form = await request.form()
    message = form.get("message", "")
    file = form.get("file")
    agent_name = form.get("agent_name", "Asistente IA")
    
    file_content_text = ""
    if file:
        # --- FREEMIUM LOCK ---
        workspace = session.get(Workspace, user.workspace_id)
        if workspace and workspace.subscription_status == "FREEMIUM":
            raise HTTPException(
                status_code=402, 
                detail="El análisis de archivos en el chat es una función exclusiva del Plan Alta. ¡Actualiza para desbloquear todo el potencial!"
            )
            
        content = await file.read()
        file_content_text = extract_text_from_file(content, file.filename)
        print(f"DEBUG AI CHAT: File received {file.filename}, length: {len(file_content_text)}")
    
    # Lógica de respuesta simulada basada en el contenido real
    if file_content_text:
        # Simulamos que lee el inicio del documento para dar realismo
        snippet = file_content_text[:150].strip().replace("\n", " ")
        response_content = f"He analizado el documento '{file.filename}' que has adjuntado. He podido extraer información clave sobre: \"{snippet}...\". \n\nEn relación a tu consulta ('{message}'), este documento parece indicar que..."
    else:
        response_content = f"Entendido. Como {agent_name} especializado en normativa laboral, he analizado tu consulta: '{message}'. Basándome en la base de conocimientos de IARESYN, te recomiendo..."
        
    return {
        "id": str(uuid.uuid4()),
        "role": "ai",
        "content": response_content,
        "timestamp": datetime.utcnow().isoformat()
    }

# --- KNOWLEDGE MANAGEMENT ---

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    text = ""
    if filename.endswith(".pdf"):
        if fitz:
            doc = fitz.open(stream=file_content, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
        else:
            text = "Error: PyMuPDF not installed."
    elif filename.endswith((".doc", ".docx")):
        if docx:
            doc = docx.Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            text = "Error: python-docx not installed."
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        # For now, just return a notification that it's an image
        text = f"Image file detected: {filename}. AI Vision will analyze this."
    else:
        text = file_content.decode("utf-8", errors="ignore")
    return text

@app.post("/api/knowledge/process-file")
async def process_knowledge_file(
    request: Request,
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    form = await request.form()
    file = form.get("file")
    doc_type = form.get("type", "legal_documents") # legal_documents, convenios, etc
    
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    content = await file.read()
    filename = file.filename
    raw_text = extract_text_from_file(content, filename)
    
    # AI Structuring Mock (Simulates LLM response)
    # In production, this would be: response = openai.ChatCompletion.create(...)
    
    # Clean up filename for title
    clean_filename = filename.replace(".pdf", "").replace(".docx", "").replace(".doc", "").replace("_", " ").replace("-", " ")
    title = clean_filename.title()
    
    # Determine type and code based on content and filename
    doc_category = "ley"
    if "Convenio" in raw_text or "CCOO" in raw_text or "UGT" in raw_text or "CONVENIO" in filename.upper():
        doc_category = "convenio"
        code = "CONV-" + str(uuid.uuid4().hex[:6]).upper()
        if "Convenio" not in title:
            title = f"Convenio: {title}"
    else:
        # Default code for legal documents
        code = "LEG-" + str(uuid.uuid4().hex[:6]).upper()
        # Only set as Estatuto if it's very clear in the name
        if "ESTATUTO" in filename.upper():
            title = "Estatuto de los Trabajadores (Versión Importada)"
            code = "RDL 2/2015"

    # Create structured object
    structured_data = {
        "title": title,
        "code": code,
        "summary": raw_text[:300] + "..." if len(raw_text) > 300 else raw_text,
        "type": "ley" if "document" in doc_type else "convenio",
        "articles": [
            {
                "number": "A-1",
                "title": "Ámbito de aplicación",
                "content": "Extracto preliminar detectado por IA en el documento subido.",
                "tags": ["importado", "ia-review"],
                "lastUpdate": datetime.utcnow().strftime("%Y-%m-%d")
            }
        ],
        "tags": ["importado", "ia-processed"],
        "raw_text_snippet": raw_text[:1000] # For auditing
    }
    
    return {
        "success": True,
        "data": structured_data
    }



@app.post("/api/admin/knowledge/sync")
async def sync_master_knowledge(
    bundle: Dict[str, Any], 
    admin: User = Depends(get_superadmin),
    session: Session = Depends(get_session)
):
    """Permite al SuperAdmin subir un bloque masivo de conocimiento (Leyes, etc.)"""
    try:
        # bundle espera: { category: [items] }
        total = 0
        for category, items in bundle.items():
            for item in items:
                # Evitar duplicados por título/código si ya existe
                existing = session.exec(
                    select(KnowledgeItem).where(
                        KnowledgeItem.title == item.get("title")
                    )
                ).first()
                
                if not existing:
                    new_item = KnowledgeItem(
                        category=category,
                        title=item.get("title"),
                        code=item.get("code"),
                        summary=item.get("summary"),
                        articles=item.get("articles", {}),
                        url=item.get("url"),
                        is_global=True
                    )
                    session.add(new_item)
                    total += 1
        
        session.commit()
        return {"success": True, "message": f"Sincronizados {total} elementos de conocimiento."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/process-url")
async def process_knowledge_url(
    request: Request,
    admin: User = Depends(get_superadmin)
):
    try:
        body = await request.json()
        url = body.get("url")
        doc_type = body.get("type", "legal_documents")
        
        if not url:
            raise HTTPException(status_code=400, detail="No URL provided")
            
        print(f"DEBUG KNOWLEDGE: Basic Text Extraction from URL: {url}")
        
        # In a real scenario, we'd use BeautifulSoup or a headless browser
        # For this robust demo, we'll use requests + basic tag stripping
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            html = resp.text
            
            # Very basic tag stripping for the mock
            import re
            clean_text = re.sub('<[^<]+?>', '', html)
            clean_text = ' '.join(clean_text.split()) # normalize whitespace
            
            # Clean title from URL
            url_part = url.split("/")[-1] or url.split("/")[-2] or "Documento Web"
            title = url_part.replace("-", " ").replace("_", " ").replace(".html", "").replace(".php", "").title()
            
            structured_data = {
                "id": str(uuid.uuid4().hex[:8]),
                "title": f"Web: {title}",
                "code": "WEB-" + str(uuid.uuid4().hex[:6]).upper(),
                "summary": clean_text[:300] + "...",
                "type": "ley" if "document" in doc_type else "convenio",
                "articles": [
                    {
                        "number": "Web-Ref",
                        "title": "Contenido extraído de URL",
                        "content": clean_text[:1000] + "...",
                        "tags": ["url-import", "ia-processed"],
                        "lastUpdate": datetime.utcnow().strftime("%Y-%m-%d")
                    }
                ],
                "source_url": url,
                "tags": ["url", "ia-processed"],
                "lastUpdate": datetime.utcnow().strftime("%Y-%m-%d")
            }
            
            return {
                "success": True,
                "data": structured_data
            }
            
        except Exception as e:
            print(f"DEBUG KNOWLEDGE: URL Error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"No se pudo acceder a la URL: {str(e)}")
            
    except Exception as ge:
        print(f"DEBUG KNOWLEDGE: Global URL error: {str(ge)}")
        raise HTTPException(status_code=500, detail=str(ge))

@app.post("/api/admin/send-test-email")
async def send_test_email(
    request: Request,
    admin: User = Depends(get_superadmin)
):
    try:
        body = await request.json()
        to_email = body.get("to")
        subject = body.get("subject", "Test desde IARESYN")
        content = body.get("content", "<h1>Hola</h1><p>Esto es un test de Resend.</p>")
        
        if not to_email:
            raise HTTPException(status_code=400, detail="No 'to' email provided")
            
        result = EmailService.send_generic_email(to_email, subject, content)
        if result:
            return {"success": True, "message": "Email enviado satisfactoriamente"}
        else:
            return {"success": False, "message": "Fallo al enviar el email"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/billing/invoices")
async def get_invoices(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if user.role == "SUPERADMIN" or user.email == "info@iaresyn.com":
        return session.exec(select(Factura)).all()
    else:
        return session.exec(select(Factura).where(Factura.workspace_id == user.workspace_id)).all()

@app.patch("/api/workspace/fiscal-data")
async def update_fiscal_data(
    data: dict,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    workspace = session.get(Workspace, user.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    workspace.razon_social = data.get("razonSocial", workspace.razon_social)
    workspace.nif = data.get("nif", workspace.nif)
    workspace.direccion_fiscal = data.get("direccionFiscal", workspace.direccion_fiscal)
    workspace.codigo_postal = data.get("codigoPostal", workspace.codigo_postal)
    workspace.ciudad = data.get("ciudad", workspace.ciudad)
    workspace.updated_at = datetime.utcnow()
    
    session.add(workspace)
    session.commit()
    return {"status": "success", "message": "Datos fiscales actualizados"}

@app.post("/api/billing/create-checkout")
async def create_checkout(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Check for fiscal data first
        workspace = session.get(Workspace, user.workspace_id)
        if not workspace or not workspace.nif or not workspace.razon_social:
            raise HTTPException(
                status_code=400, 
                detail="Debes completar tus datos fiscales en la sección de Facturación antes de realizar un pago."
            )

        body = await request.json()
        price_id = body.get("priceId")
        
        if not price_id:
            raise HTTPException(status_code=400, detail="Missing priceId")
            
        # Dynamic URLs for Production compatibility
        BASE_WEB_URL = os.getenv("FRONTEND_URL", "http://localhost:5175")
        success_url = f"{BASE_WEB_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{BASE_WEB_URL}/billing/cancel"
        
        session_stripe = StripeService.create_checkout_session(
            user.email, price_id, success_url, cancel_url
        )
        
        if session_stripe:
            return {"checkoutUrl": session_stripe.url}
        else:
            raise HTTPException(status_code=502, detail="La pasarela de Stripe no ha respondido correctamente. Verifica la configuración.")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"STRIPE ERROR: {str(e)}")
        # If it's a Stripe authentication error (invalid key)
        if "api_key" in str(e).lower() or "authentication" in str(e).lower():
            raise HTTPException(
                status_code=502, 
                detail="Error de autenticación con Stripe. Posiblemente las claves de API no son válidas."
            )
        raise HTTPException(status_code=500, detail=f"Error interno en el proceso de pago: {str(e)}")

@app.post("/api/billing/webhook")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    event = StripeService.handle_webhook_event(payload, sig_header)
    
    if not event:
        return JSONResponse(content={"status": "error"}, status_code=400)
    
    if event['type'] == 'checkout.session.completed':
        session_obj = event['data']['object']
        customer_email = session_obj.get('customer_email')
        
        # Encontrar el usuario por email para obtener el workspace
        user = session.exec(select(User).where(User.email == customer_email)).first()
        if user:
            # --- ACTIVATE WORKSPACE ---
            workspace = session.get(Workspace, user.workspace_id)
            if workspace:
                workspace.subscription_status = "ACTIVE"
                session.add(workspace)
                print(f"🚀 STRIPE WEBHOOK: Workspace {workspace.id} ACTIVADO para {customer_email}")

            # Persistir factura en DB
            nueva_factura = Factura(
                workspace_id=user.workspace_id,
                stripe_id=session_obj.get('id'),
                monto=session_obj.get('amount_total', 0) / 100, # Stripe usa céntimos
                tipo="MANTENIMIENTO" if session_obj.get('mode') == 'subscription' else "ALTA",
                pdf_url=session_obj.get('invoice_pdf') # A veces disponible en el objeto session dependiendo de la config
            )
            session.add(nueva_factura)
            session.commit()
            print(f"💰 STRIPE WEBHOOK: Factura guardada para {customer_email}")
        
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
