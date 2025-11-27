from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from database import get_connection

router = APIRouter(prefix="/dudas", tags=["Dudas y Quejas"])

class Duda(BaseModel):
    correo: EmailStr
    nombre: str
    observaciones: str | None = None


# 1️⃣ CREAR
@router.post("/")
def crear_duda(data: Duda):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO DudasYQuejas (correo, nombre, observaciones)
            VALUES (?, ?, ?)
        """, (data.correo, data.nombre, data.observaciones))

        conn.commit()
        return {"message": "✅ Duda/queja registrada correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear el registro: {e}")

    finally:
        conn.close()


# 2️⃣ LISTAR
@router.get("/")
def listar_dudas():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id_observacion, correo, nombre, observaciones
            FROM DudasYQuejas
            ORDER BY id_observacion DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        keys = ["id_observacion", "correo", "nombre", "observaciones"]
        return [dict(zip(keys, r)) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al listar dudas: {e}")


# 3️⃣ ELIMINAR
@router.delete("/{id_observacion}")
def eliminar_duda(id_observacion: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM DudasYQuejas WHERE id_observacion = ?", id_observacion)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="No existe un registro con ese ID")

        return {"message": "🗑️ Registro eliminado correctamente"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar registro: {e}")

    finally:
        conn.close()
