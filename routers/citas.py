from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/citas", tags=["Citas Médicas"])

# ---------------------------------------------------
# MODELOS
# ---------------------------------------------------
class Cita(BaseModel):
    id_usuario: int
    id_medico: int
    fecha: str
    hora: str


class ReprogramarCita(BaseModel):
    nueva_fecha: str
    nueva_hora: str


# ---------------------------------------------------
# 1️⃣ LISTAR ESPECIALIDADES DISPONIBLES
# ---------------------------------------------------
@router.get("/especialidades")
def listar_especialidades():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_especialidad, nombre FROM Especialidades")
    rows = cursor.fetchall()
    conn.close()

    return [{"id_especialidad": r[0], "nombre": r[1]} for r in rows]


# ---------------------------------------------------
# 2️⃣ BUSCAR MÉDICOS DISPONIBLES POR ESPECIALIDAD Y HORARIO
# ---------------------------------------------------
@router.get("/disponibilidad/{id_especialidad}")
def medicos_disponibles(id_especialidad: int, dia_semana: str, hora: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.id_medico, m.nombre, e.nombre AS especialidad, d.dia_semana, d.hora_inicio, d.hora_fin
        FROM Medicos m
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
        JOIN DisponibilidadMedica d ON m.id_medico = d.id_medico
        WHERE e.id_especialidad = ?
          AND d.dia_semana = ?
          AND ? BETWEEN d.hora_inicio AND d.hora_fin
    """, (id_especialidad, dia_semana, hora))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No hay médicos disponibles en ese horario")

    keys = ["id_medico", "nombre", "especialidad", "dia_semana", "hora_inicio", "hora_fin"]
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------
# 3️⃣ AGENDAR CITA MÉDICA
# ---------------------------------------------------
@router.post("/")
def agendar_cita(cita: Cita):
    conn = get_connection()
    cursor = conn.cursor()

    # Validar disponibilidad del médico
    cursor.execute("""
        SELECT COUNT(*) 
        FROM DisponibilidadMedica
        WHERE id_medico = ?
          AND DATENAME(WEEKDAY, ?) = dia_semana
          AND ? BETWEEN hora_inicio AND hora_fin
    """, (cita.id_medico, cita.fecha, cita.hora))
    disponible = cursor.fetchone()[0]

    if disponible == 0:
        raise HTTPException(status_code=400, detail="El médico no está disponible en ese horario")

    # Validar si ya tiene una cita en esa fecha/hora
    cursor.execute("""
        SELECT COUNT(*) FROM Citas
        WHERE id_medico = ? AND fecha = ? AND hora = ?
    """, (cita.id_medico, cita.fecha, cita.hora))
    ocupado = cursor.fetchone()[0]

    if ocupado > 0:
        raise HTTPException(status_code=400, detail="El médico ya tiene una cita en esa hora")

    try:
        cursor.execute("""
            INSERT INTO Citas (id_usuario, id_medico, fecha, hora, estado)
            VALUES (?, ?, ?, ?, 'Pendiente')
        """, (cita.id_usuario, cita.id_medico, cita.fecha, cita.hora))
        conn.commit()
        return {"message": "✅ Cita agendada exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al agendar cita: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 4️⃣ CANCELAR CITA
# ---------------------------------------------------
@router.put("/{id_cita}/cancelar")
def cancelar_cita(id_cita: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Citas
            SET estado='Cancelada', fecha_actualizacion=GETDATE()
            WHERE id_cita=?
        """, id_cita)
        conn.commit()
        return {"message": "🚫 Cita cancelada correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al cancelar cita: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 5️⃣ REPROGRAMAR CITA
# ---------------------------------------------------
@router.put("/{id_cita}/reprogramar")
def reprogramar_cita(id_cita: int, data: ReprogramarCita):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE Citas
            SET estado='Reprogramada',
                fecha_original = fecha,
                hora_original = hora,
                fecha = ?,
                hora = ?,
                fecha_actualizacion = GETDATE()
            WHERE id_cita = ?
        """, (data.nueva_fecha, data.nueva_hora, id_cita))
        conn.commit()
        return {"message": "🔁 Cita reprogramada correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al reprogramar cita: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 6️⃣ HISTORIAL DE CITAS DE UN PACIENTE
# ---------------------------------------------------
@router.get("/historial/{id_usuario}")
def historial_citas(id_usuario: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id_cita, m.nombre AS medico, e.nombre AS especialidad, c.fecha, c.hora, c.estado
        FROM Citas c
        JOIN Medicos m ON c.id_medico = m.id_medico
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
        WHERE c.id_usuario = ?
        ORDER BY c.fecha DESC, c.hora DESC
    """, id_usuario)

    rows = cursor.fetchall()
    conn.close()

    keys = ["id_cita", "medico", "especialidad", "fecha", "hora", "estado"]
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------
# 7️⃣ DETALLE DE CITA
# ---------------------------------------------------
@router.get("/{id_cita}")
def detalle_cita(id_cita: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id_cita, u.nombre AS paciente, m.nombre AS medico,
               e.nombre AS especialidad, c.fecha, c.hora, c.estado, c.nota_medica
        FROM Citas c
        JOIN Usuarios u ON c.id_usuario = u.id_usuario
        JOIN Medicos m ON c.id_medico = m.id_medico
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
        WHERE c.id_cita = ?
    """, id_cita)

    cita = cursor.fetchone()
    conn.close()

    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    keys = ["id_cita", "paciente", "medico", "especialidad", "fecha", "hora", "estado", "nota_medica"]
    return dict(zip(keys, cita))
