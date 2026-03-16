import os
import resend
from dotenv import load_dotenv

load_dotenv()

# Configure Resend API Key
resend.api_key = os.getenv("RESEND_API_KEY")

class EmailService:
    @staticmethod
    def send_welcome_email(to_email, first_name):
        """
        Envia un email de bienvenida a un nuevo cliente/usuario.
        """
        try:
            params = {
                "from": "IARESYN Audisyn <onboarding@resend.dev>",
                "to": [to_email],
                "subject": f"¡Bienvenido a IARESYN, {first_name}!",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #d4af37;">¡Bienvenido a la Auditoría Inteligente!</h2>
                    <p>Hola <strong>{first_name}</strong>,</p>
                    <p>Tu cuenta en <strong>IARESYN Audisyn</strong> ha sido creada correctamente.</p>
                    <p>Ahora puedes acceder a la plataforma para gestionar tus auditorías de cumplimiento laboral con el poder de la Inteligencia Artificial.</p>
                    <a href="https://iaresyn.ai" style="display: inline-block; padding: 12px 24px; background-color: #d4af37; color: #000; text-decoration: none; border-radius: 5px; font-weight: bold;">Acceder a mi Panel</a>
                    <p style="margin-top: 20px; font-size: 0.8em; color: #666;">Si no esperabas este correo, por favor contáctanos.</p>
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
