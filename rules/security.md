# Reglas de Seguridad — BLIS

## Variables de entorno
- `backend/.env` contiene `DATABASE_URL` con credenciales de Supabase, más las credenciales de los módulos clonados (Agrocalidad, Inventario LAG, Torre de Control, Auditoría de Etiquetas — ver lista completa en `CLAUDE.md` §Deploy/§Estructura)
- NUNCA commitear `.env` — ya está en `.gitignore`
- Crear `backend/.env.example` con estructura vacía para nuevos devs:
  ```
  DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
  ```

## Secretos de los módulos clonados (Fases 1-4)
- `GITHUB_TOKEN` (Agrocalidad): fine-grained PAT, dar solo el permiso mínimo (`actions:write`) sobre el repo `AgrocalidadDartis` — nunca un token de alcance amplio
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_WEBHOOK_SECRET` (Auditoría de Etiquetas): el webhook (`POST /api/auditoria-etiquetas/telegram/webhook`) valida el header `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_WEBHOOK_SECRET` — sin esa variable configurada, el endpoint acepta cualquier request sin validar origen
- `GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON`: cuenta de servicio con acceso de escritura únicamente a la carpeta de fotos de auditoría — no usar una cuenta con acceso a todo el Drive de la organización
- `UPS_CLIENT_ID/SECRET`, `FEDEX_CLIENT_ID/SECRET`, `DUOPLANE_API_KEY/PASSWORD` (Torre de Control): credenciales de terceros, mismo tratamiento que `DATABASE_URL` — nunca en el código ni en el frontend
- Ninguno de estos módulos expone sus credenciales al frontend: todo el fetch a APIs externas ocurre en `backend/app/services/*.py`

## Anti-bot y automatización
- El scraping de Agrocalidad (Playwright) corre en GitHub Actions del repo externo, no dentro de BLIS — evita correr un navegador headless en el mismo proceso web que sirve el resto de la app
- El bot RPA que escribiría tracking numbers en Dartis (Fase 3b) está **deliberadamente sin implementar**: automatizar clics en un ERP de producción sin salvaguardas (vista previa + confirmación humana, selectores robustos, verificación post-escritura) es un riesgo real de corromper datos de pedidos reales — no reactivar sin esas salvaguardas

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
