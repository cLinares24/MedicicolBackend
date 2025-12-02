from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection
import hashlib

router = APIRouter(prefix="/medicos", tags=["Médicos"])

# ---------------------------------------------------
# MODELOS
# ---------------------------------------------------

class Medico(BaseModel):
    nombre: str
    cedula: str
    correo: str
    telefono: str | None = None
    id_especialidad: int


class MedicoRegistro(BaseModel):
    nombre: str
    cedula: str
    correo: str
    telefono: str
    contrasena: str
    id_especialidad: int


class LoginMedico(BaseModel):
    correo: str
    contrasena: str


class Disponibilidad(BaseModel):
    dia_semana: str
    hora_inicio: str
    hora_fin: str

# ---------------------------------------------------
# 1️⃣ REGISTRAR MÉDICO
# ---------------------------------------------------
@router.post("/registro")
def registrar_medico(data: MedicoRegistro):
    conn = get_connection()
    cursor = conn.cursor()

    hashed_pass = hashlib.sha256(data.contrasena.encode()).hexdigest()
    hashed_pass2 = hashed_pass

    try:
        # ---------- INSERT USUARIOS (CORREGIDO) ----------
        cursor.execute("""
            INSERT INTO Usuarios (nombre, cedula, correo, contrasena, genero, rol, contrasena2)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.nombre,
            data.cedula,
            data.correo,
            hashed_pass,
            "H",
            "medico",
            hashed_pass2
        ))

        cursor.execute("SELECT SCOPE_IDENTITY()")
        id_usuario = cursor.fetchone()[0]

        # ---------- INSERT MEDICOS (CORREGIDO) ----------
        cursor.execute("""
            INSERT INTO dbo.Medicos (nombre, cedula, correo, telefono, id_especialidad)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.nombre,
            data.cedula,
            data.correo,
            data.telefono,
            data.id_especialidad
        ))

        conn.commit()
        return {"message": "Médico registrado exitosamente"}

    except Exception as e:
        conn.rollback()
        print("🔥 ERROR EXACTO:", e)   # <- Esto te mostrará el error real
        raise HTTPException(status_code=400, detail=f"Error al registrar médico: {e}")

    finally:
        conn.close()

# ---------------------------------------------------
# 2️⃣ LOGIN MÉDICO
# ---------------------------------------------------
@router.post("/login")
def login_medico(data: LoginMedico):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_pass = hashlib.sha256(data.contrasena.encode()).hexdigest()

    cursor.execute("""
        SELECT id_usuario, nombre, correo, rol
        FROM Usuarios
        WHERE correo=? AND contrasena=? AND rol='medico'
    """, (data.correo, hashed_pass))

    medico = cursor.fetchone()
    conn.close()

    if not medico:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario no es médico")

    return {
        "message": "Inicio de sesión exitoso",
        "medico": {"id": medico[0], "nombre": medico[1], "correo": medico[2], "rol": medico[3]}
    }


# ---------------------------------------------------
# 3️⃣ CONSULTAR PERFIL MÉDICO
# ---------------------------------------------------
@router.get("/{id_medico}")
def obtener_perfil_medico(id_medico: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.nombre, m.cedula, m.correo, e.nombre AS especialidad
        FROM Medicos m
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
        WHERE m.id_medico = ?
    """, id_medico)

    medico = cursor.fetchone()
    conn.close()

    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    keys = ["nombre", "cedula", "correo", "especialidad"]
    return dict(zip(keys, medico))


# ---------------------------------------------------
# 4️⃣ DEFINIR DISPONIBILIDAD
# ---------------------------------------------------
@router.post("/{id_medico}/disponibilidad")
def definir_disponibilidad(id_medico: int, data: Disponibilidad):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO DisponibilidadMedica (id_medico, dia_semana, hora_inicio, hora_fin)
            VALUES (?, ?, ?, ?)
        """, (id_medico, data.dia_semana, data.hora_inicio, data.hora_fin))
        conn.commit()
        return {"message": "✅ Disponibilidad registrada correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al registrar disponibilidad: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 5️⃣ CONSULTAR DISPONIBILIDAD
# ---------------------------------------------------
@router.get("/{id_medico}/disponibilidad")
def consultar_disponibilidad(id_medico: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT dia_semana, hora_inicio, hora_fin
        FROM DisponibilidadMedica
        WHERE id_medico = ?
    """, id_medico)
    rows = cursor.fetchall()
    conn.close()

    return [{"dia_semana": r[0], "hora_inicio": str(r[1]), "hora_fin": str(r[2])} for r in rows]


# ---------------------------------------------------
# 6️⃣ CONSULTAR CITAS PROGRAMADAS
# ---------------------------------------------------
@router.get("/{id_medico}/citas")
def consultar_citas_medico(id_medico: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id_cita, u.nombre AS paciente, c.fecha, c.hora, c.estado
        FROM Citas c
        JOIN Usuarios u ON c.id_usuario = u.id_usuario
        WHERE c.id_medico = ?
        ORDER BY c.fecha, c.hora
    """, id_medico)

    citas = cursor.fetchall()
    conn.close()

    keys = ["id_cita", "paciente", "fecha", "hora", "estado"]
    return [dict(zip(keys, c)) for c in citas]


# ---------------------------------------------------
# 7️⃣ CAMBIAR ESTADO DE CITA
# ---------------------------------------------------
class EstadoCita(BaseModel):
    estado: str

@router.put("/citas/{id_cita}/estado")
def actualizar_estado_cita(id_cita: int, data: EstadoCita):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Citas SET estado=?, fecha_actualizacion=GETDATE()
            WHERE id_cita=?
        """, (data.estado, id_cita))
        conn.commit()
        return {"message": f"✅ Cita marcada como {data.estado}"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al actualizar cita: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 8️⃣ AGREGAR NOTA MÉDICA
# ---------------------------------------------------
class NotaMedica(BaseModel):
    nota_medica: str

@router.put("/citas/{id_cita}/nota")
def agregar_nota_medica(id_cita: int, data: NotaMedica):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Citas
            SET nota_medica=?, estado='Atendida', fecha_actualizacion=GETDATE()
            WHERE id_cita=?
        """, (data.nota_medica, id_cita))
        conn.commit()
        return {"message": "✅ Nota médica agregada correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al agregar nota médica: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 3️⃣.5️⃣ OBTENER MÉDICOS POR ESPECIALIDAD
# ---------------------------------------------------
@router.get("/especialidad/{id_especialidad}")
def medicos_por_especialidad(id_especialidad: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.id_medico, m.nombre, m.cedula, m.correo, m.telefono, e.nombre AS especialidad
        FROM Medicos m
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
        WHERE m.id_especialidad = ?
    """, id_especialidad)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No hay médicos en esta especialidad")

    keys = ["id_medico", "nombre", "cedula", "correo", "telefono", "especialidad"]

    return [dict(zip(keys, r)) for r in rows]
