from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection
from typing import Optional

router = APIRouter(prefix="/citas", tags=["Citas Médicas"])

# ---------------------------------------------------
# MODELOS
# ---------------------------------------------------

class CrearCita(BaseModel):
    id_usuario: int
    id_medico: int
    id_especialidad: int
    fecha: str
    hora: str
    
class CitaCreate(BaseModel):
    id_usuario: Optional[int] = None   # opcional porque un admin puede crear sin usuario
    id_medico: int
    id_especialidad: int
    fecha: str          # YYYY-MM-DD
    hora: str           # HH:MM

class Especialidad(BaseModel):
    nombre: str
    
class ReprogramarCita(BaseModel):
    fecha: str | None = None
    hora: str | None = None
    id_medico: int | None = None


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
# 1️⃣ CREAR ESPECIALIDAD
# ---------------------------------------------------
@router.post("/especialidades")
def crear_especialidad(data: Especialidad):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Especialidades (nombre)
            VALUES (?)
        """, (data.nombre,))

        conn.commit()
        return {"message": "✅ Especialidad creada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear especialidad: {e}")

    finally:
        conn.close()

###Citas disponibles
@router.get("/disponibles/{id_especialidad}")
def horarios_disponibles(id_especialidad: int, fecha: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id_medico, m.nombre, d.hora_inicio, d.hora_fin
        FROM Medicos m
        JOIN DisponibilidadMedica d ON m.id_medico = d.id_medico
        WHERE m.id_especialidad = ?
          AND DATENAME(WEEKDAY, ?) = d.dia_semana
    """, (id_especialidad, fecha))

    disponibilidad = cursor.fetchall()

    resultados = []

    for medico_id, nombre, inicio, fin in disponibilidad:
        # buscar horas ya ocupadas
        cursor.execute("""
            SELECT hora FROM Citas 
            WHERE id_medico=? AND fecha=?
        """, (medico_id, fecha))

        horas_ocupadas = {str(r[0]) for r in cursor.fetchall()}

        hora_actual = inicio

        while hora_actual < fin:
            hora_str = str(hora_actual)

            if hora_str not in horas_ocupadas:
                resultados.append({
                    "id_medico": medico_id,
                    "medico": nombre,
                    "hora": hora_str,
                    "fecha": fecha
                })

            # sumar 1 hora
            cursor.execute("SELECT DATEADD(hour, 1, ?)", hora_actual)
            hora_actual = cursor.fetchone()[0]

    conn.close()
    return resultados


###ELIMINAR CITAS
@router.delete("/citas/{id_cita}")
def eliminar_cita(id_cita: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Citas WHERE id_cita = ?", (id_cita,))
        conn.commit()

        return {"message": "🗑️ Cita eliminada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"❌ Error al eliminar la cita: {e}")

    finally:
        conn.close()


@router.put("/citas/{id_cita}/reprogramar")
def reprogramar_cita(id_cita: int, data: ReprogramarCita):
    conn = get_connection()
    cursor = conn.cursor()

    # traer la cita actual
    cursor.execute("""
        SELECT id_medico, id_especialidad, fecha, hora 
        FROM Citas WHERE id_cita = ?
    """, (id_cita,))
    cita_actual = cursor.fetchone()

    if not cita_actual:
        raise HTTPException(status_code=404, detail="❌ La cita no existe")

    medico_actual, especialidad, fecha_actual, hora_actual = cita_actual

    # Determinar valores nuevos
    nuevo_medico = data.id_medico or medico_actual
    nueva_fecha = data.fecha or fecha_actual
    nueva_hora = data.hora or hora_actual

    # 1. Validar que el médico pertenezca a la especialidad
    cursor.execute("""
        SELECT COUNT(*) FROM Medicos 
        WHERE id_medico = ? AND id_especialidad = ?
    """, (nuevo_medico, especialidad))

    if cursor.fetchone()[0] == 0:
        raise HTTPException(
            status_code=400,
            detail="❌ El nuevo médico no pertenece a esta especialidad."
        )

    # 2. Validar que no tenga otra cita en ese horario
    cursor.execute("""
        SELECT COUNT(*) FROM Citas
        WHERE id_medico = ?
        AND fecha = ?
        AND hora = ?
        AND id_cita != ?
    """, (nuevo_medico, nueva_fecha, nueva_hora, id_cita))

    if cursor.fetchone()[0] > 0:
        raise HTTPException(
            status_code=400,
            detail="❌ El médico ya tiene una cita en ese horario."
        )

    # 3. Actualizar
    try:
        cursor.execute("""
            UPDATE Citas
            SET id_medico = ?, fecha = ?, hora = ?
            WHERE id_cita = ?
        """, (nuevo_medico, nueva_fecha, nueva_hora, id_cita))

        conn.commit()

        return {"message": "🔄 Cita reprogramada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"❌ Error al reprogramar la cita: {e}")

    finally:
        conn.close()


@router.get("", tags=["Citas Médicas"])
def listar_todas_citas():
    conn = get_connection()
    cursor = conn.cursor()
    # ejemplo: join Usuarios y Medicos para enviar email/nombre/medico
    cursor.execute("""
        SELECT c.id_cita, c.id_usuario, u.nombre as nombre_usuario, u.correo, c.id_medico, m.nombre as medico, c.id_especialidad, e.nombre as especialidad, c.fecha, c.hora
        FROM Citas c
        LEFT JOIN Usuarios u ON c.id_usuario = u.id_usuario
        LEFT JOIN Medicos m ON c.id_medico = m.id_medico
        LEFT JOIN Especialidades e ON c.id_especialidad = e.id_especialidad
        ORDER BY c.fecha DESC, c.hora DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id_cita": r[0],
            "id_usuario": r[1],
            "nombre_usuario": r[2],
            "correo": r[3],
            "id_medico": r[4],
            "medico": r[5],
            "id_especialidad": r[6],
            "especialidad": r[7],
            "fecha": r[8],
            "hora": r[9],
        })
    return result

@router.post("/")
def agendar_cita(data: CrearCita):
    conn = get_connection()
    cursor = conn.cursor()

    # validar que no esté ocupada
    cursor.execute("""
        SELECT COUNT(*) FROM Citas
        WHERE id_medico=? AND fecha=? AND hora=?
    """, (data.id_medico, data.fecha, data.hora))

    if cursor.fetchone()[0] > 0:
        raise HTTPException(400, "Ese horario ya está ocupado")

    try:
        cursor.execute("""
            INSERT INTO Citas (id_usuario, id_medico, id_especialidad, fecha, hora)
            VALUES (?, ?, ?, ?, ?)
        """, (data.id_usuario, data.id_medico, data.id_especialidad, data.fecha, data.hora))

        conn.commit()
        return {"message": "Cita agendada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(400, f"Error: {e}")
    finally:
        conn.close()
  
##CREAR CITA        
@router.post("/citas")
def crear_cita(data: CitaCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Validar que el médico pertenece a la especialidad
    cursor.execute("""
        SELECT COUNT(*) FROM Medicos
        WHERE id_medico = ? AND id_especialidad = ?
    """, (data.id_medico, data.id_especialidad))

    if cursor.fetchone()[0] == 0:
        raise HTTPException(
            status_code=400,
            detail="❌ El médico no pertenece a esa especialidad."
        )

    # 2. Validar que el médico NO tenga otra cita en la misma fecha/hora
    cursor.execute("""
        SELECT COUNT(*) FROM Citas
        WHERE id_medico = ? AND fecha = ? AND hora = ?
    """, (data.id_medico, data.fecha, data.hora))

    if cursor.fetchone()[0] > 0:
        raise HTTPException(
            status_code=400,
            detail="❌ El médico ya tiene una cita en ese horario."
        )

    # 3. Insertar la cita
    try:
        cursor.execute("""
            INSERT INTO Citas (id_usuario, id_medico, id_especialidad, fecha, hora, estado, nota_medica)
            VALUES (?, ?, ?, ?, ?, 'Pendiente', NULL)
        """, (
            data.id_usuario,
            data.id_medico,
            data.id_especialidad,
            data.fecha,
            data.hora
        ))

        conn.commit()

        return {"message": "✅ Cita creada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"❌ Error creando la cita: {e}"
        )
    finally:
        conn.close()
