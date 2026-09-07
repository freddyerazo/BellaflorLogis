import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# pool_pre_ping: antes de entregar una conexion del pool, hace un "SELECT 1"
# liviano; si esta muerta, la descarta y abre una nueva -- transparente para
# quien llama. Sin esto, un proceso de larga duracion (el pool de conexiones
# de Supabase/PgBouncer recicla conexiones inactivas del lado del servidor)
# revienta con "server closed the connection unexpectedly" a mitad de un
# lote, encontrado en la practica interpretando recibos con Claude durante
# varios minutos seguidos. pool_recycle es una segunda red de seguridad:
# fuerza a renovar cualquier conexion que lleve mas de 30 min abierta, antes
# de que el pooler decida cerrarla el solo.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
