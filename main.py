from fastapi import FastAPI
from routers import usuarios, medicos, citas, admin, notificaciones, dudas
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="MediciCol API")

origins = [
    "http://localhost:3000",
    "https://medicicol.site"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],        
    allow_headers=["*"],         
)
app.include_router(usuarios.router)
app.include_router(medicos.router)
app.include_router(citas.router)
app.include_router(admin.router)
app.include_router(notificaciones.router)
app.include_router(dudas.router)

@app.get("/")
def root():
    return {"message": "API MediciCol funcionando 🔥"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
