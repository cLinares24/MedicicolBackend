from fastapi import APIRouter, HTTPException
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from decouple import config

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

# ---------------------------------------------------
# CONFIGURACIÓN DEL SERVIDOR DE CORREO
# ---------------------------------------------------
conf = ConnectionConfig(
    MAIL_USERNAME=config("MAIL_USERNAME"),
    MAIL_PASSWORD=config("MAIL_PASSWORD"),
    MAIL_FROM=config("MAIL_FROM"),
    MAIL_PORT=config("MAIL_PORT", cast=int),
    MAIL_SERVER=config("MAIL_SERVER"),
    MAIL_FROM_NAME=config("MAIL_FROM_NAME"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

# ---------------------------------------------------
# MODELOS
# ---------------------------------------------------
class NotificacionCita(BaseModel):
    correo: EmailStr
    nombre_usuario: str
    fecha: str
    hora: str
    medico: str

class NotificacionCitaCancelada(BaseModel):
    correo: EmailStr
    nombre_usuario: str
    medico: str
    fecha: str
    hora: str


# ---------------------------------------------------
# 1️⃣ CONFIRMACIÓN DE CITA
# ---------------------------------------------------
@router.post("/cita-confirmada")
async def enviar_confirmacion_cita(data: NotificacionCita):
    mensaje = MessageSchema(
        subject="✅ Confirmación de cita médica - MediciCol",
        recipients=[data.correo],
        body=f"""
        Hola {data.nombre_usuario},

        Tu cita médica ha sido confirmada:
        🩺 Médico: {data.medico}
        📅 Fecha: {data.fecha}
        ⏰ Hora: {data.hora}

        ¡Te esperamos puntual!
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(mensaje)
        return {"message": "📨 Correo de confirmación enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")


# ---------------------------------------------------
# 2️⃣ RECORDATORIO DE CITA
# ---------------------------------------------------
@router.post("/recordatorio")
async def enviar_recordatorio_cita(data: NotificacionCita):
    mensaje = MessageSchema(
        subject="⏰ Recordatorio de cita médica - MediciCol",
        recipients=[data.correo],
        body=f"""
        Hola {data.nombre_usuario},

        Este es un recordatorio de tu cita médica:
        🩺 Médico: {data.medico}
        📅 Fecha: {data.fecha}
        ⏰ Hora: {data.hora}

        ¡No faltes! Recuerda llegar unos minutos antes.
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(mensaje)
        return {"message": "📨 Correo de recordatorio enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")


# ---------------------------------------------------
# 3️⃣ CITA CANCELADA / REPROGRAMADA
# ---------------------------------------------------
class NotificacionCambio(BaseModel):
    correo: EmailStr
    nombre_usuario: str
    medico: str
    motivo: str  # "cancelada" o "reprogramada"
    nueva_fecha: str | None = None
    nueva_hora: str | None = None


@router.post("/cita-cambio")
async def enviar_cambio_cita(data: NotificacionCambio):
    if data.motivo == "cancelada":
        body = f"""
        Hola {data.nombre_usuario},

        Lamentamos informarte que tu cita médica con {data.medico} ha sido cancelada.
        Por favor, comunícate con nosotros si deseas reagendarla.

        Equipo MediciCol 💙
        """
    else:
        body = f"""
        Hola {data.nombre_usuario},

        Tu cita médica con {data.medico} ha sido reprogramada:
        📅 Nueva fecha: {data.nueva_fecha}
        ⏰ Nueva hora: {data.nueva_hora}

        Equipo MediciCol 💙
        """

    mensaje = MessageSchema(
        subject=f"🔄 Cita {data.motivo} - MediciCol",
        recipients=[data.correo],
        body=body,
        subtype="plain"
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(mensaje)
        return {"message": f"📨 Correo de cita {data.motivo} enviado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")


###Cita cancelada
@router.post("/cita-cancelada")
async def enviar_cita_cancelada(data: NotificacionCitaCancelada):

    mensaje = MessageSchema(
        subject="❌ Tu cita ha sido cancelada - MediciCol",
        recipients=[data.correo],
        body=f"""
        Hola {data.nombre_usuario},

        Queremos informarte que tu cita ha sido cancelada:
        
        🩺 Médico: {data.medico}
        📅 Fecha: {data.fecha}
        ⏰ Hora: {data.hora}

        Si deseas volver a agendar la cita, puedes hacerlo desde nuestra plataforma
        o contactando al equipo de soporte.

        Equipo MediciCol 💙
        """,
        subtype="plain"
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(mensaje)
        return {"message": "📨 Notificación de cita cancelada enviada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")
