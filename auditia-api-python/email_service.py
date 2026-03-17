import os
import resend
from dotenv import load_dotenv

load_dotenv()

# Configure Resend API Key
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailService:
    @staticmethod
    def send_welcome_email(to_email, first_name, password=None):
        """
        Envia un email de bienvenida a un nuevo cliente/usuario incluyendo sus credenciales.
        """
        try:
            credentials_html = ""
            if password:
                credentials_html = f"""
                <div style="background-color: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; margin: 20px 0; color: #fff;">
                    <h3 style="margin-top: 0; color: #d4af37; font-size: 16px;">Tus Credenciales de Acceso:</h3>
                    <p style="margin: 8px 0;"><strong>Usuario:</strong> <span style="color: #ccc;">{to_email}</span></p>
                    <p style="margin: 8px 0;"><strong>Contraseña Temporal:</strong> <code style="background: #333; padding: 4px 8px; border-radius: 4px; color: #d4af37;">{password}</code></p>
                    <p style="font-size: 12px; color: #888; margin-top: 12px;">* Se recomienda cambiar la contraseña tras el primer inicio de sesión.</p>
                </div>
                """

            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            params = {
                "from": "IARESYN Audisyn <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"🚀 Bienvenido a IARESYN, {first_name}",
                "html": f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: auto; padding: 30px; background-color: #050505; color: #ffffff; border-radius: 16px; border: 1px solid #222;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #d4af37; margin: 0; font-size: 28px; letter-spacing: 1px;">IARESYN</h1>
                        <p style="color: #888; margin: 5px 0 0; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">Auditoría Inteligencia Laboral</p>
                    </div>
                    
                    <h2 style="color: #fff; font-size: 22px;">¡Hola, {first_name}!</h2>
                    <p style="line-height: 1.6; color: #ccc;">Es un placer darte la bienvenida a <strong>IARESYN</strong>. Tu entorno de trabajo ya está configurado y listo para empezar.</p>
                    
                    {credentials_html}
                    
                    <p style="line-height: 1.6; color: #ccc;">Ahora puedes acceder a la plataforma para gestionar tus auditorías de cumplimiento laboral con el apoyo de nuestra IA especializada.</p>
                    
                    <div style="text-align: center; margin-top: 35px;">
                        <a href="{frontend_url}" style="display: inline-block; padding: 14px 30px; background-color: #d4af37; color: #000; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; transition: 0.3s;">Acceder a mi Panel</a>
                    </div>
                    
                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #222; text-align: center;">
                        <p style="font-size: 12px; color: #555;">© 2026 IARESYN AI. Todos los derechos reservados.<br>Este es un email automático, por favor no respondas directamente.</p>
                    </div>
                </div>
                """
            }
            email = resend.Emails.send(params)
            return email
        except Exception as e:
            print(f"Error al enviar email: {str(e)}")
            return None

    @staticmethod
    def send_generic_email(to_email, subject, content_html):
        """
        Envia un email genérico.
        """
        try:
            params = {
                "from": "IARESYN Audisyn <noreply@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": content_html
            }
            email = resend.Emails.send(params)
            return email
        except Exception as e:
            print(f"Error al enviar email genérico: {str(e)}")
            return None
