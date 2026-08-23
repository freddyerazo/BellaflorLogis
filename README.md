# BLIS — Bellaflor Logistics Intelligence System

Sistema interno de Bellaflor Group para análisis, simulación y gestión de costos logísticos de exportación de flores. Centraliza datos de Dartis (ventas), Google Apps Script (ingresos locales) y Supabase en una interfaz única.

Desde agosto de 2026, BLIS también centraliza 4 herramientas que antes vivían como proyectos externos independientes: consulta de requisitos fitosanitarios (**Agrocalidad**), inventario en la bodega de Miami (**Inventario LAG**), conciliación de cajas contra UPS/FedEx (**Torre de Control**), auditoría de despachos de clientes especiales vía bot de Telegram (**Auditoría de Etiquetas**) y la generación del EDI para el carrier Armellini (**Armellini Post**).

**Producción:** https://blis-hxu1.onrender.com
**Documentación técnica completa (con código fuente):** [`BLIS_DOCUMENTACION.md`](BLIS_DOCUMENTACION.md)
**Contexto de proyecto para asistentes de IA:** [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md)

## Stack

FastAPI (Python) + Vanilla JS/HTML/CSS + PostgreSQL (Supabase). Sin build step en el frontend.

## Arrancar en local

```bash
git clone https://github.com/freddyerazo/BellaflorLogis.git
cd BellaflorLogis
python -m venv .venv
.venv\Scripts\activate          # Windows — source .venv/bin/activate en Linux/Mac
pip install -r backend/requirements.txt
```

Crear `backend/.env` con al menos `DATABASE_URL` (ver [`CLAUDE.md`](CLAUDE.md) para la lista completa de variables por módulo). Luego:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Abrir `http://localhost:8000`.

## Estructura

```
backend/app/api/       # un router por módulo
backend/app/services/  # lógica reutilizable (clientes externos, motores de conciliación)
backend/app/schemas/   # modelos Pydantic
frontend/pages/        # un .html + un .js por módulo
database/migrations/   # migraciones SQL aplicadas directo en Supabase
```

Más detalle en [`CLAUDE.md`](CLAUDE.md) (estructura completa, rutas API, deuda técnica) y [`rules/`](rules/) (convenciones de código y seguridad).
