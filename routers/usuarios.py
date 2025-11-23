from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from database import get_connection
import hashlib

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

# ---- Esquema Pydantic ----
class Usuario(BaseModel):
    nombre: str
    cedula: str
    correo: str
    contrasena: str
    contrasena2: str
    genero: str | None = None
    rol: str = "paciente"  # valor por defecto


# ---- 1️⃣ Registrar usuario ----
@router.post("/registro")
def registrar_usuario(usuario: Usuario):
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos")

    cursor = conn.cursor()

    # Validar que las contraseñas coincidan
    if usuario.contrasena != usuario.contrasena2:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden")

    # Encriptar las contraseñas
    hashed_pass = hashlib.sha256(usuario.contrasena.encode()).hexdigest()
    hashed_pass2 = hashlib.sha256(usuario.contrasena2.encode()).hexdigest()

    try:
        cursor.execute("""
            INSERT INTO Usuarios (nombre, cedula, correo, contrasena, genero, rol, contrasena2)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (usuario.nombre, usuario.cedula, usuario.correo,
              hashed_pass, usuario.genero, usuario.rol, hashed_pass2))
        conn.commit()
        return {"message": "✅ Usuario registrado exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error al registrar usuario: {e}")
    finally:
        conn.close()


# ---- 2️⃣ Login ----
class LoginData(BaseModel):
    correo: str
    contrasena: str

@router.post("/login")
def login(data: LoginData):
    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos")

    cursor = conn.cursor()
    hashed_pass = hashlib.sha256(data.contrasena.encode()).hexdigest()

    cursor.execute("SELECT id_usuario, nombre, correo, rol FROM Usuarios WHERE correo=? AND contrasena=?", 
                   (data.correo, hashed_pass))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    return {
        "message": "Inicio de sesión exitoso",
        "usuario": {
            "id": user[0],
            "nombre": user[1],
            "correo": user[2],
            "rol": user[3]
        }
    }


# ---- 3️⃣ Obtener perfil ----
@router.get("/{id_usuario}")
def obtener_perfil(id_usuario: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nombre, cedula, correo, genero, rol, fecha_registro
        FROM Usuarios
        WHERE id_usuario=?
    """, id_usuario)

    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    keys = ["nombre", "cedula", "correo", "genero", "rol", "fecha_registro"]
    return dict(zip(keys, user))
