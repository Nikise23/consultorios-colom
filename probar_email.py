#!/usr/bin/env python3
"""
Script para probar el envío de emails de confirmación de turnos
"""

import os
import sys
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

def enviar_email_prueba(destinatario):
    """Enviar email de prueba"""
    try:
        # Obtener configuración
        mail_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        mail_port = int(os.environ.get('MAIL_PORT', 587))
        mail_use_tls = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
        mail_username = os.environ.get('MAIL_USERNAME', '')
        mail_password = os.environ.get('MAIL_PASSWORD', '')
        mail_from = os.environ.get('MAIL_FROM', mail_username)
        
        print("=" * 60)
        print("CONFIGURACIÓN DE EMAIL")
        print("=" * 60)
        print(f"Servidor: {mail_server}")
        print(f"Puerto: {mail_port}")
        print(f"TLS: {mail_use_tls}")
        print(f"Usuario: {mail_username}")
        print(f"Desde: {mail_from}")
        print(f"Destinatario: {destinatario}")
        print("=" * 60)
        print()
        
        if not mail_username or not mail_password:
            print("❌ ERROR: MAIL_USERNAME o MAIL_PASSWORD no están configurados")
            print("   Verifica que el archivo .env tenga estas variables")
            return False
        
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Prueba de Email - Consultorios Colom'
        msg['From'] = mail_from
        msg['To'] = destinatario
        
        # Cuerpo del email
        texto = f"""
Estimado/a,

Este es un email de prueba del sistema de reserva de turnos.

Si recibes este email, significa que la configuración está funcionando correctamente.

Detalles de prueba:
- Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- Sistema: Consultorios Colom
- Función: Confirmación de turnos

Saludos cordiales,
Sistema de Consultorio
        """
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .info-box {{ background: white; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; border-radius: 5px; }}
        .success {{ background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Email de Prueba</h1>
        </div>
        <div class="content">
            <p>Estimado/a,</p>
            
            <div class="success">
                <strong>¡Éxito!</strong> Si recibes este email, significa que la configuración está funcionando correctamente.
            </div>
            
            <div class="info-box">
                <h3>Detalles de la Prueba:</h3>
                <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p><strong>Sistema:</strong> Consultorios Colom</p>
                <p><strong>Función:</strong> Confirmación de turnos</p>
            </div>
            
            <p>Este es un email de prueba del sistema de reserva de turnos.</p>
            
            <p>Cuando un paciente reserve un turno, recibirá un email similar con los detalles de su turno.</p>
            
            <p>Saludos cordiales,<br><strong>Sistema de Consultorio</strong></p>
        </div>
        <div class="footer">
            <p>Este es un email automático de prueba.</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Adjuntar partes
        part1 = MIMEText(texto, 'plain', 'utf-8')
        part2 = MIMEText(html, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        print("📧 Enviando email...")
        
        # Enviar email
        server = smtplib.SMTP(mail_server, mail_port)
        server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Email enviado exitosamente!")
        print(f"   Revisa la bandeja de entrada de: {destinatario}")
        print("   (También revisa la carpeta de spam si no lo ves)")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ ERROR de autenticación: {e}")
        print("\nPosibles causas:")
        print("  - Usuario o contraseña incorrectos")
        print("  - Si usas Gmail, asegúrate de usar una 'Contraseña de Aplicación'")
        print("  - Verifica que la verificación en 2 pasos esté activada en Gmail")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ ERROR SMTP: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    email_destino = "nicfer0508@gmail.com"
    
    if len(sys.argv) > 1:
        email_destino = sys.argv[1]
    
    print("\n🧪 PRUEBA DE ENVÍO DE EMAIL")
    print("=" * 60)
    print(f"Enviando email de prueba a: {email_destino}")
    print()
    
    resultado = enviar_email_prueba(email_destino)
    
    if resultado:
        print("\n✅ Prueba completada exitosamente")
    else:
        print("\n❌ La prueba falló. Revisa la configuración.")
        sys.exit(1)

