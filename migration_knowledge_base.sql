-- IARESYN Knowledge Base Migration Script
-- Target: Supabase (PostgreSQL)

-- 1. Create Tables
CREATE TABLE IF NOT EXISTS legal_documents (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    code TEXT,
    summary TEXT,
    last_update DATE
);

CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT REFERENCES legal_documents(id) ON DELETE CASCADE,
    number TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT[],
    last_update DATE
);

CREATE TABLE IF NOT EXISTS convenios (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    code TEXT,
    scope TEXT,
    vigencia TEXT,
    status TEXT,
    tags TEXT[]
);

CREATE TABLE IF NOT EXISTS jurisprudencia (
    id TEXT PRIMARY KEY,
    tribunal TEXT,
    sentencia TEXT NOT NULL,
    tema TEXT,
    date DATE,
    relevancia TEXT,
    summary TEXT,
    tags TEXT[]
);

-- 2. Seed Data (based on legalKnowledge.js)

-- Legal Documents
INSERT INTO legal_documents (id, type, title, code, summary, last_update) VALUES
('ET_2015', 'ley', 'Estatuto de los Trabajadores', 'RDL 2/2015', 'Norma básica que regula las relaciones laborales en España.', '2026-01-15'),
('LPRL_1995', 'ley', 'Ley de Prevención de Riesgos Laborales', 'Ley 31/1995', 'Marco legal para la seguridad y salud de los trabajadores.', '2025-12-01'),
('LO_IGUALDAD_2007', 'ley', 'Ley Orgánica de Igualdad', 'LO 3/2007', 'Regulación de los planes de igualdad y medidas contra la discriminación.', '2025-03-01')
ON CONFLICT (id) DO NOTHING;

-- Articles
INSERT INTO articles (document_id, number, title, content, tags, last_update) VALUES
('ET_2015', '34.9', 'Registro de jornada', 'La empresa garantizará el registro diario de jornada, que deberá incluir el horario concreto de inicio y finalización de la jornada de trabajo de cada persona trabajadora...', ARRAY['jornada', 'obligatorio', 'registro'], '2023-05-12'),
('ET_2015', '27', 'Salario Mínimo Interprofesional', 'El Gobierno fijará, previa consulta con las organizaciones sindicales y asociaciones empresariales más representativas, anualmente, el salario mínimo interprofesional...', ARRAY['salario', 'SMI', 'remuneración'], '2024-02-01'),
('LPRL_1995', '14', 'Derecho a la protección frente a los riesgos laborales', 'Los trabajadores tienen derecho a una protección eficaz en materia de seguridad y salud en el trabajo.', ARRAY['PRL', 'salud', 'seguridad'], '2025-12-01'),
('LO_IGUALDAD_2007', '45', 'Planes de igualdad', 'Las empresas están obligadas a respetar la igualdad de trato y de oportunidades en el ámbito laboral...', ARRAY['igualdad', 'planes', 'brecha'], '2025-03-01')
ON CONFLICT DO NOTHING;

-- Convenios
INSERT INTO convenios (id, title, code, scope, vigencia, status, tags) VALUES
('CONV_CONS_2024', 'Convenio Estatal de Consultoría y TIC', '99012025012204', 'Nacional', '2024-2027', 'Vigente', ARRAY['TIC', 'Consultoría', 'Oficinas']),
('CONV_OFF_2022', 'Convenio de Oficinas y Despachos', '99001015011981', 'Nacional', '2022-2025', 'Vigente', ARRAY['Oficinas', 'Administración'])
ON CONFLICT (id) DO NOTHING;

-- Jurisprudencia
INSERT INTO jurisprudencia (id, tribunal, sentencia, tema, date, relevancia, summary, tags) VALUES
('STS_234_2025', 'Tribunal Supremo', 'STS 234/2025', 'Horas extras no registradas - presunción de fraude', '2026-01-15', 'Alta', 'El TS dictamina que la ausencia de registro horario genera una presunción de realización de horas extras si hay indicios razonables.', ARRAY['horas extras', 'registro', 'fraude']),
('STS_DISCO_2024', 'Tribunal Supremo', 'STS 112/2024', 'Derecho a la desconexión digital fuera del horario laboral', '2024-11-20', 'Muy Alta', 'Establece el derecho del trabajador a no responder comunicaciones empresariales fuera de su jornada, reforzando la paz familiar y personal.', ARRAY['desconexión digital', 'conciliación', 'derechos digitales'])
ON CONFLICT (id) DO NOTHING;
