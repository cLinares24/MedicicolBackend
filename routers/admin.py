from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from database import get_connection

router = APIRouter(prefix="/admin", tags=["Administración"])

class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    correo: str | None = None
    cedula: str | None = None
    genero: str | None = None
    rol: str | None = None
    

class MedicoUpdate(BaseModel):
    nombre: str | None = None
    cedula: str | None = None
    correo: str | None = None
    telefono: str | None = None
    id_especialidad: int | None = None  # <- debe ser opcional

# ---------------------------------------------------
# 1️⃣ LISTAR TODOS LOS USUARIOS
# ---------------------------------------------------
@router.get("/usuarios")
def listar_usuarios(rol: str | None = None):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id_usuario, nombre, cedula, correo, rol, fecha_registro FROM Usuarios WHERE rol = 'paciente'"
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
# 1️⃣ LISTAR TODOS LOS MÉDICOS
# ---------------------------------------------------
@router.get("/medicos")
def listar_medicos():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            m.id_medico,
            m.nombre,
            m.cedula,
            m.correo,
            m.telefono,
            e.nombre AS especialidad
        FROM Medicos m
        JOIN Especialidades e ON m.id_especialidad = e.id_especialidad
    """)

    rows = cursor.fetchall()
    conn.close()

    keys = ["id_medico", "nombre", "cedula", "correo", "telefono", "especialidad"]
    return [dict(zip(keys, r)) for r in rows]



# ---------------------------------------------------
# 2️⃣ EDITAR USUARIO / MÉDICO
# ---------------------------------------------------
@router.put("/usuarios/{id_usuario}")
def editar_usuario(id_usuario: int, data: UsuarioUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    campos = []
    valores = []

    if data.nombre:
        campos.append("nombre=?")
        valores.append(data.nombre)

    if data.correo:
        campos.append("correo=?")
        valores.append(data.correo)

    if data.cedula:
        campos.append("cedula=?")
        valores.append(data.cedula)

    if data.genero:
        campos.append("genero=?")
        valores.append(data.genero)

    if data.rol:
        campos.append("rol=?")
        valores.append(data.rol)

    if not campos:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    query = f"UPDATE Usuarios SET {', '.join(campos)} WHERE id_usuario=?"
    valores.append(id_usuario)

    try:
        cursor.execute(query, tuple(valores))
        conn.commit()
        return {"message": "Usuario actualizado correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al actualizar usuario: {e}")
    finally:
        conn.close()
        
        # ---------------------------------------------------
# ✏️ EDITAR MÉDICO (y su usuario asociado)
# ---------------------------------------------------
@router.put("/medicos/{id_medico}")
def editar_medico(id_medico: int, data: MedicoUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1️⃣ Obtener el correo del médico
        cursor.execute("SELECT correo FROM Medicos WHERE id_medico=?", id_medico)
        medico = cursor.fetchone()

        if not medico:
            raise HTTPException(status_code=404, detail="Médico no encontrado")

        correo_actual = medico[0]

        # 2️⃣ Obtener el id_usuario asociado
        # cursor.execute("SELECT id_usuario FROM Usuarios WHERE correo=?", correo_actual)
        cursor.execute("""
    SELECT U.id_usuario 
    FROM Usuarios U
    JOIN Medicos M ON U.correo = M.correo
    WHERE M.id_medico = ?
""", (id_medico,))

        usuario = cursor.fetchone()

        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario asociado no encontrado")

        id_usuario = usuario[0]

        # 3️⃣ Construir updates dinámicos para Medicos
        campos_medicos = []
        valores_medicos = []

        if data.nombre:
            campos_medicos.append("nombre=?")
            valores_medicos.append(data.nombre)

        if data.cedula:
            campos_medicos.append("cedula=?")
            valores_medicos.append(data.cedula)

        if data.correo:
            campos_medicos.append("correo=?")
            valores_medicos.append(data.correo)

        if data.telefono:
            campos_medicos.append("telefono=?")
            valores_medicos.append(data.telefono)

        # 4️⃣ Construir updates dinámicos para Usuarios
        campos_usuarios = []
        valores_usuarios = []

        if data.nombre:
            campos_usuarios.append("nombre=?")
            valores_usuarios.append(data.nombre)

        if data.cedula:
            campos_usuarios.append("cedula=?")
            valores_usuarios.append(data.cedula)

        if data.correo:
            campos_usuarios.append("correo=?")
            valores_usuarios.append(data.correo)

        # 5️⃣ Ejecutar UPDATE en Medicos
        if campos_medicos:
            query_medico = f"UPDATE Medicos SET {', '.join(campos_medicos)} WHERE id_medico=?"
            valores_medicos.append(id_medico)
            cursor.execute(query_medico, tuple(valores_medicos))

        # 6️⃣ Ejecutar UPDATE en Usuarios
        if campos_usuarios:
            query_usuario = f"UPDATE Usuarios SET {', '.join(campos_usuarios)} WHERE id_usuario=?"
            valores_usuarios.append(id_usuario)
            cursor.execute(query_usuario, tuple(valores_usuarios))

        conn.commit()
        return {"message": "📝 Médico actualizado correctamente"}

    except Exception as e:
        conn.rollback()
        print("🔥 ERROR EXACTO:", e)   # <- Esto te mostrará el error real
        raise HTTPException(status_code=400, detail=f"Error al actualizar médico: {e}")

    finally:
        conn.close()


# ---------------------------------------------------
# 3️⃣ ELIMINAR USUARIO
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
# 3️⃣ ELIMINAR MÉDICO
# ---------------------------------------------------
@router.delete("/medicos/{id_medico}")
def eliminar_medico(id_medico: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1️⃣ Buscar el correo del médico
        # cursor.execute("SELECT correo FROM Medicos WHERE id_medico=?", id_medico)
        cursor.execute("DELETE FROM Medicos WHERE id_medico=?", id_medico)

        conn.commit()
        return {"message": "🗑️ Médico y usuario eliminados correctamente"}

    except Exception as e:
        conn.rollback()
        print("🔥 ERROR EXACTO:", e)   # <- Esto te mostrará el error real
        raise HTTPException(status_code=400, detail=f"Error al eliminar médico: {e}")

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
