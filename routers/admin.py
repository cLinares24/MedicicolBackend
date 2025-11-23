from fastapi import APIRouter, HTTPException, Query
from database import get_connection

router = APIRouter(prefix="/admin", tags=["Administración"])

# ---------------------------------------------------
# 1️⃣ LISTAR TODOS LOS USUARIOS
# ---------------------------------------------------
@router.get("/usuarios")
def listar_usuarios(rol: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id_usuario, nombre, cedula, correo, rol, fecha_registro FROM Usuarios"
    params = []

    if rol:
        query += " WHERE rol = ?"
        params.append(rol)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    keys = ["id_usuario", "nombre", "cedula", "correo", "rol", "fecha_registro"]
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------
# 2️⃣ EDITAR USUARIO / MÉDICO
# ---------------------------------------------------
@router.put("/usuarios/{id_usuario}")
def editar_usuario(id_usuario: int, nombre: str | None = None, correo: str | None = None, rol: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    campos = []
    valores = []

    if nombre:
        campos.append("nombre=?")
        valores.append(nombre)
    if correo:
        campos.append("correo=?")
        valores.append(correo)
    if rol:
        campos.append("rol=?")
        valores.append(rol)

    if not campos:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    query = f"UPDATE Usuarios SET {', '.join(campos)} WHERE id_usuario=?"
    valores.append(id_usuario)

    try:
        cursor.execute(query, tuple(valores))
        conn.commit()
        return {"message": "✅ Usuario actualizado correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al actualizar usuario: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 3️⃣ ELIMINAR USUARIO / MÉDICO
# ---------------------------------------------------
@router.delete("/usuarios/{id_usuario}")
def eliminar_usuario(id_usuario: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Usuarios WHERE id_usuario=?", id_usuario)
        conn.commit()
        return {"message": "🗑️ Usuario eliminado correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar usuario: {e}")
    finally:
        conn.close()


# ---------------------------------------------------
# 4️⃣ LISTAR TODAS LAS CITAS (FILTRAR POR ESTADO O FECHA)
# ---------------------------------------------------
@router.get("/citas")
def listar_citas(estado: str | None = None, fecha: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT c.id_cita, u.nombre AS paciente, m.nombre AS medico,
               e.nombre AS especialidad, c.fecha, c.hora, c.estado
        FROM Citas c
        JOIN Usuarios u ON c.id_usuario = u.id_usuario
        JOIN Medicos m ON c.id_medico = m.id_medico
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
    """

    params = []
    filtros = []

    if estado:
        filtros.append("c.estado = ?")
        params.append(estado)
    if fecha:
        filtros.append("c.fecha = ?")
        params.append(fecha)

    if filtros:
        query += " WHERE " + " AND ".join(filtros)

    query += " ORDER BY c.fecha DESC, c.hora DESC"

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    keys = ["id_cita", "paciente", "medico", "especialidad", "fecha", "hora", "estado"]
    return [dict(zip(keys, r)) for r in rows]


# ---------------------------------------------------
# 5️⃣ ESTADÍSTICAS BÁSICAS DEL SISTEMA
# ---------------------------------------------------
@router.get("/estadisticas")
def estadisticas():
    conn = get_connection()
    cursor = conn.cursor()

    # Total de pacientes
    cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE rol='paciente'")
    pacientes = cursor.fetchone()[0]

    # Total de médicos
    cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE rol='medico'")
    medicos = cursor.fetchone()[0]

    # Total de citas
    cursor.execute("SELECT COUNT(*) FROM Citas")
    citas_totales = cursor.fetchone()[0]

    # Citas atendidas
    cursor.execute("SELECT COUNT(*) FROM Citas WHERE estado='Atendida'")
    atendidas = cursor.fetchone()[0]

    # Citas canceladas
    cursor.execute("SELECT COUNT(*) FROM Citas WHERE estado='Cancelada'")
    canceladas = cursor.fetchone()[0]

    conn.close()

    return {
        "pacientes_registrados": pacientes,
        "medicos_registrados": medicos,
        "citas_totales": citas_totales,
        "citas_atendidas": atendidas,
        "citas_canceladas": canceladas
    }
