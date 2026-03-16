-- IARESYN Core Audit Schema (Updated for Production)
-- Target: Supabase (PostgreSQL)

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Tables

-- Workspaces (Multi-tenancy)
CREATE TABLE IF NOT EXISTS workspace (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cif TEXT,
    razon_social TEXT,
    nif TEXT,
    direccion_fiscal TEXT,
    codigo_postal TEXT,
    ciudad TEXT,
    subscription_status TEXT DEFAULT 'FREEMIUM',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS user_table ( -- 'user' is a reserved keyword in Postgres
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    role TEXT DEFAULT 'ADMIN',
    workspace_id TEXT REFERENCES workspace(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enterprises
CREATE TABLE IF NOT EXISTS empresa (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspace(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    cif TEXT NOT NULL,
    sector TEXT,
    num_empleados INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audits
CREATE TABLE IF NOT EXISTS auditoria (
    id TEXT PRIMARY KEY,
    empresa_id TEXT REFERENCES empresa(id) ON DELETE CASCADE,
    estado TEXT DEFAULT 'Borrador',
    tipo TEXT DEFAULT 'FULL',
    progreso INTEGER DEFAULT 0,
    current_step INTEGER DEFAULT 1,
    wizard_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Findings (Hallazgos)
CREATE TABLE IF NOT EXISTS hallazgo (
    id TEXT PRIMARY KEY,
    auditoria_id TEXT REFERENCES auditoria(id) ON DELETE CASCADE,
    control_id TEXT,
    resultado TEXT DEFAULT 'NO CUMPLE',
    remediacion TEXT DEFAULT 'Abierto',
    severidad TEXT DEFAULT 'Media',
    descripcion TEXT,
    recomendacion TEXT,
    exposicion_min FLOAT DEFAULT 0.0,
    exposicion_max FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents
CREATE TABLE IF NOT EXISTS documento (
    id TEXT PRIMARY KEY,
    empresa_id TEXT REFERENCES empresa(id) ON DELETE CASCADE,
    hallazgo_id TEXT REFERENCES hallazgo(id) ON DELETE SET NULL,
    nombre TEXT NOT NULL,
    tipo TEXT,
    url TEXT NOT NULL,
    relacionado_tipo TEXT DEFAULT 'Ninguno',
    relacionado_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Invoices (Facturas)
CREATE TABLE IF NOT EXISTS factura (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspace(id) ON DELETE CASCADE,
    stripe_id TEXT,
    monto FLOAT NOT NULL,
    moneda TEXT DEFAULT 'EUR',
    fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tipo TEXT DEFAULT 'ALTA',
    estado TEXT DEFAULT 'PAGADA',
    pdf_url TEXT
);

-- Master Knowledge Library
CREATE TABLE IF NOT EXISTS knowledgeitem (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    code TEXT,
    summary TEXT,
    articles JSONB DEFAULT '{}',
    url TEXT,
    is_global BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
