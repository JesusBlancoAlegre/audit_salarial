from audit_salarial_app.models import Alerta, Auditoria, Empresa, Usuario
from audit_salarial_app.extensions import db
import logging

def generar_alerta(auditoria_id, tipo, severidad, asunto, mensaje, canal='AMBOS'):
    """
    Genera un registro de alerta in-app y lanza (o mockea) el envío de email.
    """
    try:
        auditoria = db.session.get(Auditoria, auditoria_id)
        if not auditoria:
            return False, "Auditoría no encontrada."

        # Identificar al usuario cliente dueño de la empresa, o al admin
        if auditoria.cliente_usuario_id:
            usuario_id = auditoria.cliente_usuario_id
        else:
            # Buscar el primer admin si no hay cliente (para testing)
            admin = Usuario.query.filter(Usuario.rol.has(nombre='ADMIN')).first()
            usuario_id = admin.id if admin else None

        alerta = Alerta(
            auditoria_id=auditoria_id,
            empresa_id=auditoria.empresa_id,
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
                except Exception as e_mail:
                    logging.error(f"Error al enviar email a {usuario.email}: {str(e_mail)}")
                    # No fallamos la transacción general si el correo falla
                    
        return True, "Alerta generada correctamente."
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error generando alerta: {str(e)}")
        return False, str(e)
