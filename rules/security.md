# Reglas de Seguridad — BLIS

## Variables de entorno
- `backend/.env` contiene `DATABASE_URL` con credenciales de Supabase
- NUNCA commitear `.env` — ya está en `.gitignore`
- Crear `backend/.env.example` con estructura vacía para nuevos devs:
  ```
  DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
  ```

## CORS
- `main.py` usa `allow_origins=["*"]` — válido en desarrollo local
- En producción cambiar a dominio específico:
  ```python
  allow_origins=["https://blis.bellaflor.com"]
  ```

## Supabase RLS
- Todas las tablas tienen RLS habilitado
- Conexión actual es directa vía SQLAlchemy (service role implícita)
- Cuando se implemente auth de usuarios, revisar políticas RLS por tabla

## Frontend
- No exponer `DATABASE_URL` ni credenciales en ningún archivo JS
- `api.js` solo habla con `/api/*` — el backend es el único que toca Supabase

## Git — antes de cada push
- Verificar que `backend/.env` NO aparece en `git status`
- Verificar que `.venv/` y `.venv-1/` NO están siendo trackeados
- `git status` debe mostrar solo archivos de código fuente
