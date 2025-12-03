FROM python:3.12-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    curl \
    gpg \
    apt-transport-https \
    unixodbc \
    unixodbc-dev \
    build-essential

# Descargar claves de Microsoft y agregar repositorio ODBC
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/microsoft-prod.list

# Instalar el driver ODBC 18
RUN apt-get update && apt-get install -y msodbcsql18

# Crear directorio de la app
WORKDIR /app

# Copiar archivos del backend
COPY . /app

# Instalar dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto para uvicorn
EXPOSE 8000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
