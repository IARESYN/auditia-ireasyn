const express = require('express');
const { PrismaClient } = require('@prisma/client');
const cors = require('cors');
require('dotenv').config();

const app = express();
const prisma = new PrismaClient();
const PORT = process.env.PORT || 8000;

app.use(cors());
app.use(express.json());

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'secret_laboral_auditia_2026';

// ─── MIDDLEWARE ───────────────────────────────────────────────────
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) return res.status(401).json({ error: 'Token no proporcionado' });

    jwt.verify(token, JWT_SECRET, (err, user) => {
        if (err) return res.status(403).json({ error: 'Token inválido o expirado' });
        req.user = user;
        next();
    });
};

// ─── AUTH ROUTES ──────────────────────────────────────────────────
app.post('/api/auth/register', async (req, res) => {
    const { email, password, name, workspaceName } = req.body;
    try {
        const hashedPassword = await bcrypt.hash(password, 10);

        // Crear Workspace y Usuario en una transacción
        const result = await prisma.$transaction(async (tx) => {
            const workspace = await tx.workspace.create({
                data: { name: workspaceName || `Empresa de ${name}` }
            });
            const user = await tx.user.create({
                data: {
                    email,
                    password: hashedPassword,
                    firstName: name,
                    workspaceId: workspace.id
                }
            });
            return { user, workspace };
        });

        res.json({ message: 'Registro exitoso' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/auth/login', async (req, res) => {
    const { email, password } = req.body;
    try {
        const user = await prisma.user.findUnique({
            where: { email },
            include: { workspace: true }
        });

        if (!user || !(await bcrypt.compare(password, user.password))) {
            return res.status(401).json({ error: 'Credenciales inválidas' });
        }

        const token = jwt.sign(
            { userId: user.id, workspaceId: user.workspaceId, role: user.role },
            JWT_SECRET,
            { expiresIn: '24h' }
        );

        res.json({
            token,
            user: {
                id: user.id,
                email: user.email,
                name: user.firstName,
                workspace: user.workspace
            }
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ─── HEALTH CHECK ─────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date() });
});

// ─── WORKSPACES ───────────────────────────────────────────────────
app.get('/api/workspaces', authenticateToken, async (req, res) => {
    try {
        // En un sistema multi-tenant estricto, un usuario solo ve su workspace
        const workspaces = await prisma.workspace.findMany({
            where: { id: req.user.workspaceId }
        });
        res.json(workspaces);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ─── EMPRESAS ─────────────────────────────────────────────────────
app.get('/api/empresas', authenticateToken, async (req, res) => {
    try {
        const empresas = await prisma.empresa.findMany({
            where: { workspaceId: req.user.workspaceId }
        });
        res.json(empresas);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/empresas', authenticateToken, async (req, res) => {
    try {
        const empresa = await prisma.empresa.create({
            data: {
                ...req.body,
                workspaceId: req.user.workspaceId
            }
        });
        res.json(empresa);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ─── AUDITORIAS ───────────────────────────────────────────────────
app.get('/api/auditorias', authenticateToken, async (req, res) => {
    const { empresaId } = req.query;
    try {
        const auditorias = await prisma.auditoria.findMany({
            where: {
                empresa: {
                    id: empresaId,
                    workspaceId: req.user.workspaceId // Validación de tenant
                }
            },
            include: { empresa: true }
        });
        res.json(auditorias);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/auditorias/:id', authenticateToken, async (req, res) => {
    try {
        const audit = await prisma.auditoria.findFirst({
            where: {
                id: req.params.id,
                empresa: { workspaceId: req.user.workspaceId }
            },
            include: { empresa: true, hallazgos: true }
        });
        if (!audit) return res.status(404).json({ error: 'Auditoría no encontrada' });
        res.json(audit);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/auditorias', authenticateToken, async (req, res) => {
    try {
        // Validar que la empresa pertenece al workspace
        const empresa = await prisma.empresa.findFirst({
            where: { id: req.body.empresaId, workspaceId: req.user.workspaceId }
        });
        if (!empresa) return res.status(403).json({ error: 'Acceso denegado a la empresa' });

        const auditoria = await prisma.auditoria.create({
            data: req.body
        });
        res.json(auditoria);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.patch('/api/auditorias/:id', authenticateToken, async (req, res) => {
    try {
        const auditoria = await prisma.auditoria.update({
            where: {
                id: req.params.id,
                empresa: { workspaceId: req.user.workspaceId }
            },
            data: req.body
        });
        res.json(auditoria);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ─── SERVER START ────────────────────────────────────────────────
app.listen(PORT, () => {
    console.log(`🚀 Auditia Backend running on http://localhost:${PORT}`);
});
