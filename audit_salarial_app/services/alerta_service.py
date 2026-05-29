from audit_salarial_app.models import Alerta, Auditoria, Empresa, Usuario
from audit_salarial_app.extensions import db
import logging
import smtplib
def generar_alerta(auditoria_id, tipo, severidad, asunto, mensaje, canal='AMBOS', empresa_id=None, usuario_id=None):
    """
    Genera un registro de alerta in-app y lanza (o mockea) el envío de email.
    Si auditoria_id es None, se requiere empresa_id o es un aviso global (a los ADMIN).
    """
    try:
        auditoria = None
        if auditoria_id:
            auditoria = db.session.get(Auditoria, auditoria_id)
            if not auditoria:
                return False, "Auditoría no encontrada."
            
            # Usar empresa de la auditoría si no se especifica
            if not empresa_id:
                empresa_id = auditoria.empresa_id
            
            # Si no hay usuario_id, usar cliente de la auditoría o admin
            if not usuario_id:
                if auditoria.cliente_usuario_id:
                    usuario_id = auditoria.cliente_usuario_id
                else:
                    admin = Usuario.query.filter(Usuario.rol.has(nombre='ADMIN')).first()
                    usuario_id = admin.id if admin else None
                    
        # Si aún no hay usuario_id (por ejemplo, auditoria_id es None), enviar al Admin por defecto
        if not usuario_id:
            admin = Usuario.query.filter(Usuario.rol.has(nombre='ADMIN')).first()
            usuario_id = admin.id if admin else None

        alerta = Alerta(
            auditoria_id=auditoria_id,
            empresa_id=empresa_id,
            usuario_id=usuario_id,
            tipo=tipo,
            severidad=severidad,
            canal=canal,
            asunto=asunto,
            mensaje=mensaje
        )
        db.session.add(alerta)
        db.session.commit()
        
        if canal in ('AMBOS', 'EMAIL') and usuario_id:
            usuario = db.session.get(Usuario, usuario_id)
            if usuario and usuario.email:
                from flask_mail import Message
                from flask import render_template
                from audit_salarial_app.extensions import mail
                
                try:
                    html_body = render_template('admin/alerta_email.html', alerta=alerta, usuario=usuario, auditoria=auditoria)
                    
                    msg = Message(asunto, recipients=[usuario.email])
                    msg.html = html_body
                    mail.send(msg)
                    
                    logging.info(f"💌 [EMAIL ENVIADO] Alerta enviada a {usuario.email} - Asunto: {asunto}")
                    alerta.enviada = True
                    from datetime import datetime
                    alerta.enviada_en = datetime.utcnow()
                    db.session.commit()
                except smtplib.SMTPException as smtp_err:
                    logging.error(f"Error SMTP enviando alerta a {usuario.email}: {str(smtp_err)}")
                except Exception as e_mail:
                    logging.error(f"Error general al enviar email a {usuario.email}: {str(e_mail)}")
                    # No fallamos la transacción general si el correo falla
                    
        return True, "Alerta generada correctamente."
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error generando alerta: {str(e)}")
        return False, str(e)
