import os
import stripe
from dotenv import load_dotenv

load_dotenv()

# Configure Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    @staticmethod
    def create_checkout_session(customer_email, price_id, success_url, cancel_url):
        """
        Crea una sesión de Checkout para el pago inicial (Alta de 599€) 
        o para la suscripción mensual (99€).
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=customer_email,
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription' if 'sub' in price_id else 'payment',
                success_url=success_url,
                cancel_url=cancel_url,
                invoice_creation={
                    'enabled': True, # Habilitar creación de factura automática
                } if 'sub' not in price_id else None,
                billing_address_collection='required',
            )
            return session
        except Exception as e:
            print(f"Error creando sesión de Stripe: {str(e)}")
            return None

    @staticmethod
    def handle_webhook_event(payload, sig_header):
        """
        Maneja los eventos de Webhook de Stripe (pagos exitosos, facturas generadas).
        """
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return event
        except Exception as e:
            print(f"Error en Webhook de Stripe: {str(e)}")
            return None

    @staticmethod
    def setup_automated_invoicing():
        """
        Nota técnica: Para que Stripe envíe el PDF automáticamente por email, 
        debe activarse en el Dashboard de Stripe -> Settings -> Billing -> Invoices: 
        'Email finalized invoices to customers'. 
        Esta función sirve como recordatorio de configuración.
        """
        pass
