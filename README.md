# BLIS — Bellaflor Logistics Intelligence System

Sistema interno de Bellaflor Group para análisis, simulación y gestión de costos logísticos de exportación de flores. Centraliza datos de Dartis (ventas), Google Apps Script (ingresos locales) y Supabase en una interfaz única.

Desde agosto de 2026, BLIS también centraliza 4 herramientas que antes vivían como proyectos externos independientes: consulta de requisitos fitosanitarios (**Agrocalidad**), inventario en la bodega de Miami (**Inventario LAG**), conciliación de cajas contra UPS/FedEx (**Torre de Control**), auditoría de despachos de clientes especiales vía bot de Telegram (**Auditoría de Etiquetas**) y la generación del EDI para el carrier Armellini (**Armellini Post**).

**Producción:** https://blis-hxu1.onrender.com
**Documentación técnica completa (con código fuente):** [`BLIS_DOCUMENTACION.md`](BLIS_DOCUMENTACION.md)
**Contexto de proyecto para asistentes de IA:** [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md)

## Stack

FastAPI (Python) + Vanilla JS/HTML/CSS + PostgreSQL (Supabase). Sin build step en el frontend.

## Arrancar en local

El entorno virtual vive **fuera del repositorio**, en `C:\dev\venvs\blis`: el proyecto está dentro de OneDrive, y OneDrive deshidrata los archivos sincronizados — eso rompe tanto los paquetes instalados como git.

```powershell
git clone https://github.com/freddyerazo/BellaflorLogis.git
cd BellaflorLogis
python -m venv C:\dev\venvs\blis
C:\dev\venvs\blis\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Crear `backend/.env` con al menos `DATABASE_URL` (ver [`CLAUDE.md`](CLAUDE.md) para la lista completa de variables por módulo). Luego, desde la raíz del repo:

```powershell
.\scripts\dev.ps1              # http://localhost:8000
.\scripts\dev.ps1 -Port 8010   # otro puerto
```

El script verifica que existan el venv y el `.env` antes de arrancar. En Linux/Mac no aplica la ruta `C:\dev`: basta un venv propio y `uvicorn app.main:app --reload` desde `backend/`. Para hacerlo a mano en Windows:

```powershell
cd backend
C:\dev\venvs\blis\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Comprobar que responde: `/health` devuelve `{"status":"ok"}` y `/db-test` confirma la conexión a Supabase.

## Estructura

```
backend/app/api/       # un router por módulo
backend/app/services/  # lógica reutilizable (clientes externos, motores de conciliación)
backend/app/schemas/   # modelos Pydantic
frontend/pages/        # un .html + un .js por módulo
database/migrations/   # migraciones SQL aplicadas directo en Supabase
```

Más detalle en [`CLAUDE.md`](CLAUDE.md) (estructura completa, rutas API, deuda técnica) y [`rules/`](rules/) (convenciones de código y seguridad).
