# Guía de Despliegue a Producción: Auditia

Esta guía detalla los pasos para poner en marcha el entorno de producción (Cloud) manteniendo el coste en $0.

## 1. Configuración de la Base de Datos (Supabase)
Google Cloud no ofrece SQL gratuito. Usaremos **Supabase** (PostgreSQL).
1. Crea un proyecto en [Supabase](https://supabase.com).
2. Obtén la `Connection String` de PostgreSQL.
3. Ejecuta el archivo `schema_audit_data.sql` en el SQL Editor de Supabase para crear las tablas.

## 2. Despliegue del Backend (Google Cloud Run)
1. Conecta tu repositorio de GitHub `IARESYN/auditia-ireasyn` a **Google Cloud Build** o usa la CLI.
2. Crea un **Service** en Cloud Run apuntando a la carpeta `/auditia-api-python`.
3. **Variables de Entorno (Secrets)**: Configura estas variables en Cloud Run:
   - `DATABASE_URL`: Tu URL de Supabase.
   - `STRIPE_SECRET_KEY`: Tu llave real (live o test).
   - `STRIPE_WEBHOOK_SECRET`: El secreto del webhook de producción.
   - `RESEND_API_KEY`: Tu llave de Resend.
   - `FIREBASE_PROJECT_ID`: El ID de tu proyecto Firebase.

## 3. Despliegue del Frontend (Firebase Hosting)
1. En la carpeta `/auditia`, ejecuta:
   ```bash
   npm install
   npm run build
   ```
2. Instala Firebase CLI: `npm install -g firebase-tools`.
3. Login e inicialización:
   ```bash
   firebase login
   firebase init hosting  # Selecciona la carpeta 'dist'
   ```
4. **Variable de Entorno**: En el panel de Vercel/Firebase (o en un archivo `.env.production`), configura:
   - `VITE_API_URL`: La URL que te asigne Google Cloud Run (ej: `https://auditia-backend-xyz.a.run.app/api`).
5. Despliegue final:
   ```bash
   firebase deploy
   ```

## 4. Conexión de Seguridad (CORS)
En el archivo `main.py` del backend, asegúrate de añadir la URL de tu frontend de producción a la lista de `origins` permitidos en el middleware de CORS.

---
**Nota**: Para cualquier duda técnica, contacta con el equipo de Auditia.
