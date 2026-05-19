"""
chat_service.py
---------------
Gestiona la creación de mensajes de chat interno entre cliente y auditor.
Los mensajes se persisten en la base de datos (tabla chat_mensaje)
y sobreviven al cierre de sesión/aplicación.
"""
import logging
from datetime import datetime

from ..extensions import db
from ..models import ChatMensaje, Auditoria, Usuario


def crear_mensaje(auditoria_id: int, autor: Usuario, contenido: str) -> ChatMensaje:
    """
    Persiste un ChatMensaje en la base de datos.

    Returns:
        El objeto ChatMensaje recién guardado.
    """
    auditoria = db.session.get(Auditoria, auditoria_id)
    if not auditoria:
        raise ValueError(f"Auditoría {auditoria_id} no encontrada.")

    contenido = contenido.strip()
    if not contenido:
        raise ValueError("El mensaje no puede estar vacío.")
    if len(contenido) > 2000:
        raise ValueError("El mensaje no puede superar los 2 000 caracteres.")

    msg = ChatMensaje(
        auditoria_id=auditoria_id,
        autor_id=autor.id,
        contenido=contenido,
        creado_en=datetime.utcnow(),
    )
    db.session.add(msg)
    db.session.commit()

    logging.info(
        f"[CHAT] Mensaje #{msg.id} de usuario {autor.id} en auditoría #{auditoria_id}"
    )

    return msg


def obtener_mensajes(auditoria_id: int, after_id: int = 0) -> list[ChatMensaje]:
    """
    Devuelve los mensajes de una auditoría, opcionalmente desde un id dado
    (para polling incremental).
    """
    q = ChatMensaje.query.filter_by(auditoria_id=auditoria_id)
    if after_id:
        q = q.filter(ChatMensaje.id > after_id)
    return q.order_by(ChatMensaje.creado_en.asc()).all()
