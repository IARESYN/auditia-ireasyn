from typing import List, Optional, Dict, Any
from sqlmodel import Field, Relationship, SQLModel, create_engine, Session, select
from datetime import datetime
import uuid

from sqlalchemy import JSON

# --- MODELS ---

class Workspace(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    cif: Optional[str] = None # Legacy
    razon_social: Optional[str] = None
    nif: Optional[str] = None
    direccion_fiscal: Optional[str] = None
    codigo_postal: Optional[str] = None
    ciudad: Optional[str] = None
    subscription_status: str = Field(default="FREEMIUM") # FREEMIUM, ACTIVE
    settings: Dict[str, Any] = Field(default={}, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    empresas: List["Empresa"] = Relationship(back_populates="workspace")
    users: List["User"] = Relationship(back_populates="workspace")

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(index=True, unique=True)
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = Field(default="ADMIN") # ADMIN, USER
    workspace_id: str = Field(foreign_key="workspace.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    workspace: Workspace = Relationship(back_populates="users")

class Empresa(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspace.id")
    nombre: str
    cif: str
    sector: Optional[str] = None
    num_empleados: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    workspace: Workspace = Relationship(back_populates="empresas")
    auditorias: List["Auditoria"] = Relationship(back_populates="empresa")

class Auditoria(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    codigo: Optional[str] = Field(default=None, index=True) # AUD-0001, etc
    empresa_id: str = Field(foreign_key="empresa.id")
    estado: str = Field(default="Borrador")
    tipo: str = Field(default="FULL")
    progreso: int = Field(default=0)
    current_step: int = Field(default=1)
    wizard_data: Dict[str, Any] = Field(default={}, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    empresa: Empresa = Relationship(back_populates="auditorias")
    hallazgos: List["Hallazgo"] = Relationship(back_populates="auditoria")

class Hallazgo(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    auditoria_id: str = Field(foreign_key="auditoria.id")
    control_id: Optional[str] = None
    resultado: str = Field(default="NO CUMPLE")
    remediacion: str = Field(default="Abierto")
    severidad: Optional[str] = Field(default="Media")
    descripcion: Optional[str] = None
    recomendacion: Optional[str] = None
    exposicion_min: float = Field(default=0.0)
    exposicion_max: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    auditoria: Auditoria = Relationship(back_populates="hallazgos")
    documentos: List["Documento"] = Relationship(back_populates="hallazgo")

class Documento(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    empresa_id: str = Field(foreign_key="empresa.id")
    hallazgo_id: Optional[str] = Field(default=None, foreign_key="hallazgo.id")
    nombre: str
    tipo: Optional[str] = None
    url: str
    relacionado_tipo: str = Field(default="Ninguno")
    relacionado_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    hallazgo: Optional[Hallazgo] = Relationship(back_populates="documentos")

class Factura(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    workspace_id: str = Field(foreign_key="workspace.id")
    stripe_id: Optional[str] = None
    monto: float
    moneda: str = Field(default="EUR")
    fecha: datetime = Field(default_factory=datetime.utcnow)
    tipo: str = Field(default="ALTA") # ALTA, MANTENIMIENTO
    estado: str = Field(default="PAGADA")
    pdf_url: Optional[str] = None
    
    workspace: Workspace = Relationship()

class KnowledgeItem(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    category: str # leyes, convenios, decretos, jurisprudencia
    title: str
    code: Optional[str] = None
    summary: Optional[str] = None
    articles: Optional[Dict[str, Any]] = Field(default={}, sa_type=JSON)
    url: Optional[str] = None
    is_global: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
