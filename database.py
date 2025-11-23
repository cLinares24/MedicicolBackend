import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{os.getenv('DRIVER')}}};"
            f"SERVER={os.getenv('DB_SERVER')};"
            f"DATABASE={os.getenv('DB_NAME')};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "Trusted_Connection=yes;"
        )
        return conn
    except Exception as e:
        print("❌ Error al conectar con la base de datos:", e)
        return None
