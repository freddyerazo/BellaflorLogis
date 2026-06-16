# Estilo de Código — BLIS

## Backend (FastAPI / Python)

### Estructura de un router
```python
# backend/app/api/especies.py
from fastapi import APIRouter, HTTPException
from app.database.connection import engine
from app.schemas.especies import EspecieOut

router = APIRouter()

@router.get("/especies", response_model=list[EspecieOut])
def get_especies():
    with engine.connect() as conn:
        ...
```

### Convenciones
- Un archivo por tabla en `api/` y `schemas/`
- Nombres de rutas en español y plural: `/especies`, `/variedades`, `/tipos-caja`
- Response model siempre definido con Pydantic
- Errores HTTP semánticos: 404 si no existe, 422 si validación falla
- Respuesta lista: `return rows` / Respuesta paginada: `{"data": rows, "total": n}`

## Frontend (Vanilla JS)

### Patrón de página estándar
Cada página (`pages/foo.html` + `pages/foo.js`) sigue este patrón:
```js
import { apiGet, apiPost, apiPut, apiDelete } from '../js/api.js';

// 1. Cargar datos al iniciar
async function init() {
  const data = await apiGet('/foo');
  renderTabla(data);
}

// 2. Renderizar tabla
function renderTabla(items) {
  const tbody = document.querySelector('#tabla-foo tbody');
  tbody.innerHTML = '';
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="4">Sin registros</td></tr>';
    return;
  }
  items.forEach(item => {
    tbody.innerHTML += `<tr>...</tr>`;
  });
}

document.addEventListener('DOMContentLoaded', init);
```

### Convenciones JS
- `camelCase` para variables y funciones
- Sin `console.log` en código que va a producción
- Siempre manejar errores con `try/catch` en llamadas async
- Comentarios en español

### Convenciones HTML
- IDs de tablas: `tabla-especies`, `tabla-variedades`, etc.
- IDs de formularios: `form-especie`, `form-variedad`, etc.
- IDs de modales: `modal-especie`, `modal-variedad`, etc.
- Clases CSS reutilizables del archivo `styles.css` global

## Git
- Formato de commits: `feat:`, `fix:`, `refactor:`, `docs:`
- Ejemplos:
  - `feat: agregar endpoint /api/mercados`
  - `fix: corregir cálculo de peso volumétrico`
  - `docs: actualizar CLAUDE.md con nuevas rutas`
- Una funcionalidad por commit, no mezclar cambios de backend y frontend salvo que sean inseparables
