from fastapi import FastAPI
from routers import usuarios, medicos, citas, admin, notificaciones

app = FastAPI(title="MediciCol API")

app.include_router(usuarios.router)
app.include_router(medicos.router)
app.include_router(citas.router)
app.include_router(admin.router)
app.include_router(notificaciones.router)

@app.get("/")
def root():
    return {"message": "API MediciCol funcionando 🔥"}
