<!-- Assisted by Antigravity (SI) — reviewed by Jeshua -->
# SpectraHive API — Referencia de Endpoints (OpenAPI 3.1)

> Esquema OpenAPI exportado en [`openapi.json`](./openapi.json).
> Contratos alineados a [`00-contexto-general.md`](../context/00-contexto-general.md) §6 sin alterar formatos ni alcance.
> Todos los ejemplos usan las coordenadas J2000 reales de **Barnard's Star**: `ra=269.452075`, `dec=4.693365`, `fov=2`.

Documentación interactiva al levantar el servidor:
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- Esquema JSON: `GET /openapi.json`

## Resumen de endpoints

| Método | Ruta | Tag | Propósito |
|---|---|---|---|
| `GET` | `/health` | `health` | Verificación de disponibilidad y estado de configuración (`DATABASE_URL`) |
| `GET` | `/cutout` | `cutouts` | Cutout infrarrojo J2000 (IRSA precalculado o fallback sintético) |
| `POST` | `/diff` | `diffs` | Alineación entera + resta `\|B - A\|` + umbral y candidatos |
| `POST` | `/report` | `reports` | Registro de anomalía o cuadrante limpio (`RN-02`/`RN-03`) |
| `POST` | `/report/{reporte_id}/validate` | `reports` | Voto de validación cruzada y confirmación en `>= 3` votos (`RF-12`, `RN-06`) |
| `GET` | `/quadrants` | `quadrants`, `dna` | Cola fija ordenada de cuadrantes (`RF-05`) |
| `GET` | `/dna/{objeto}` | `quadrants`, `dna` | Firma espectral visual precalculada del ADN Cósmico (`RF-14`, `RF-15`) |

---

## 1. `GET /health`

| Campo | Detalle |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/health` |
| **Tag** | `health` |
| **Parámetros** | Ninguno |
| **Respuesta exitosa** | `200 OK` — `HealthResponse` (`status`, `service`, `database_configured`) |
| **Códigos de error** | Ninguno |

**Ejemplo de request:**
```bash
curl -s http://127.0.0.1:8000/health
```

**Ejemplo de response (`200 OK`):**
```json
{
  "status": "ok",
  "service": "spectrahive-backend",
  "database_configured": true
}
```

---

## 2. `GET /cutout`

| Campo | Detalle |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/cutout` |
| **Tag** | `cutouts` |
| **Parámetros (query)** | `ra` *(requerido, string)*: RA J2000 decimal `0–360` o sexagesimal (`"269.452075"` / `"17h57m"`).<br>`dec` *(requerido, string)*: Dec J2000 decimal `-90..+90` o sexagesimal (`"4.693365"` / `"+4d41m"`).<br>`fov` *(opcional, int, default `2`)*: Solo `1` o `2` (`RF-02`).<br>`epoca` *(opcional, string, default `"A"`)*: `"A"`/`"DR1"` o `"B"`/`"QR3"` (`RF-06`).<br>`format` *(opcional, string, default `"json"`)*: `"json"` o `"png"`. |
| **Respuesta exitosa** | `200 OK` — `CutoutResponse` JSON (`{ra, dec, fov, epoca, fuente, objeto, imagen}`) o binario `image/png` si `format=png`. |
| **Códigos de error** | `400 Bad Request` (`ErrorResponse`): coordenadas fuera de rango (`RA` no en `[0, 360]` o `Dec` no en `[-90, 90]`), formato inválido o `fov` distinto de `1` o `2`.<br>`422 Unprocessable Content` (`HTTPValidationError`): falta parámetro requerido `ra`/`dec` o `fov` no entero. |

**Ejemplo de request:**
```bash
curl -s "http://127.0.0.1:8000/cutout?ra=269.452075&dec=4.693365&fov=2&epoca=A"
```

**Ejemplo de response (`200 OK`):**
```json
{
  "ra": 269.452075,
  "dec": 4.693365,
  "fov": 2,
  "epoca": "DR1",
  "fuente": "irsa",
  "objeto": "Barnard's Star",
  "imagen": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Ejemplo de error (`400 Bad Request`):**
```json
{
  "detail": "RA fuera de rango valido (0 a 360 grados): 400.0."
}
```

---

## 3. `POST /diff`

| Campo | Detalle |
|---|---|
| **Método** | `POST` |
| **Ruta** | `/diff` |
| **Tag** | `diffs` |
| **Parámetros (JSON body)** | `cuadrante_id` *(requerido, string)*: UUID del cuadrante o nombre del objeto (ej. `"Barnard's Star"`).<br>`epoca_a` *(opcional, string, default `"A"`)*: Época base (`"A"`/`"DR1"`).<br>`epoca_b` *(opcional, string, default `"B"`)*: Época destino (`"B"`/`"QR3"`).<br>`ra` *(opcional, float \| string \| null)*: Sobrescribe RA J2000 si no se consulta por ID.<br>`dec` *(opcional, float \| string \| null)*: Sobrescribe Dec J2000 si no se consulta por ID.<br>`fov` *(opcional, int, default `2`)*: Solo `1` o `2`. |
| **Respuesta exitosa** | `200 OK` — `DiffResponse` (`{umbral, candidatos: [{ra, dec, valor, motivo, tipo}], imagen, fuente, cuadrante_id}`). |
| **Códigos de error** | `400 Bad Request` (`ErrorResponse`): coordenadas o `fov` inválidos.<br>`404 Not Found` (`ErrorResponse`): `cuadrante_id` no encontrado.<br>`422 Unprocessable Content` (`HTTPValidationError`): body JSON inválido o falta `cuadrante_id`. |

**Ejemplo de request:**
```bash
curl -s -X POST "http://127.0.0.1:8000/diff" \
  -H "Content-Type: application/json" \
  -d '{
    "cuadrante_id": "Barnard'\''s Star",
    "epoca_a": "DR1",
    "epoca_b": "QR3",
    "ra": 269.452075,
    "dec": 4.693365,
    "fov": 2
  }'
```

**Ejemplo de response (`200 OK`):**
```json
{
  "umbral": 0.4125,
  "candidatos": [
    {
      "ra": 269.4512,
      "dec": 4.6941,
      "valor": 1.0,
      "motivo": "Desplazamiento dipolar de 8.6 px entre Epoca A y B con variacion delta=142.30 sobre el umbral (movimiento propio rapido)",
      "tipo": "movimiento"
    }
  ],
  "imagen": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "fuente": "irsa",
  "cuadrante_id": "Barnard's Star"
}
```

**Ejemplo de error (`404 Not Found`):**
```json
{
  "detail": "Cuadrante 'desconocido' no encontrado."
}
```

---

## 4. `POST /report`

| Campo | Detalle |
|---|---|
| **Método** | `POST` |
| **Ruta** | `/report` |
| **Tag** | `reports` |
| **Parámetros (JSON body)** | `cuadrante_id` *(requerido, string)*: UUID o nombre del cuadrante en BD.<br>`ra` *(requerido, float \| string)*: RA J2000 del punto reportado (`269.452075`).<br>`dec` *(requerido, float \| string)*: Dec J2000 del punto reportado (`4.693365`).<br>`tipo` *(requerido, string)*: `"movimiento"`, `"brillo"` o `"limpio"`. Debe coincidir con `tipo_prueba` del cuadrante, salvo `"limpio"` (`RN-02`/`RN-03`). |
| **Respuesta exitosa** | `201 Created` — `CreateReportResponse` (`{reporte_id, estado, cuadrante_id, tipo}`). |
| **Códigos de error** | `400 Bad Request` (`ErrorResponse`): coordenadas inválidas, tipo desconocido o cruce indebido de grupo (`movimiento` sobre objeto `brillo` como RW Aurigae/R Draconis).<br>`404 Not Found` (`ErrorResponse`): cuadrante no encontrado.<br>`422 Unprocessable Content` (`HTTPValidationError`): body incompleto.<br>`503 Service Unavailable` (`ErrorResponse`): falta `DATABASE_URL` en el entorno. |

**Ejemplo de request:**
```bash
curl -s -X POST "http://127.0.0.1:8000/report" \
  -H "Content-Type: application/json" \
  -d '{
    "cuadrante_id": "Barnard'\''s Star",
    "ra": 269.452075,
    "dec": 4.693365,
    "tipo": "movimiento"
  }'
```

**Ejemplo de response (`201 Created`):**
```json
{
  "reporte_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "estado": "pendiente",
  "cuadrante_id": "00000000-0000-0000-0000-000000000001",
  "tipo": "movimiento"
}
```

**Ejemplo de error (`400 Bad Request` — cruce RN-02/RN-03):**
```json
{
  "detail": "El cuadrante 'RW Aurigae' pertenece al grupo 'brillo'; no se permite reportar 'movimiento' (RN-02/RN-03)."
}
```

---

## 5. `POST /report/{reporte_id}/validate`

| Campo | Detalle |
|---|---|
| **Método** | `POST` |
| **Ruta** | `/report/{reporte_id}/validate` |
| **Tag** | `reports` |
| **Parámetros** | Path: `reporte_id` *(requerido, string)*: UUID del reporte.<br>Body JSON: `coincide` *(requerido, boolean)*, `es_simulado` *(opcional, boolean, default `false` — `true` para votos simulados de demo según `RF-13`)*. |
| **Respuesta exitosa** | `201 Created` — `ValidateReportResponse` (`{validacion_id, reporte_id, coincide, es_simulado, etiqueta, votos_coinciden, confirmado, estado_cuadrante}`). |
| **Códigos de error** | `400 Bad Request` (`ErrorResponse`): intento de validar un reporte `"limpio"` (`RF-11`).<br>`404 Not Found` (`ErrorResponse`): reporte no encontrado.<br>`422 Unprocessable Content` (`HTTPValidationError`): body inválido.<br>`503 Service Unavailable` (`ErrorResponse`): falta `DATABASE_URL` en el entorno. |

**Ejemplo de request:**
```bash
curl -s -X POST "http://127.0.0.1:8000/report/a1b2c3d4-e5f6-7890-abcd-ef1234567890/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "coincide": true,
    "es_simulado": true
  }'
```

**Ejemplo de response (`201 Created`, 3er voto que confirma):**
```json
{
  "validacion_id": "f1e2d3c4-b5a6-7890-1234-567890abcdef",
  "reporte_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "coincide": true,
  "es_simulado": true,
  "etiqueta": "simulado",
  "votos_coinciden": 3,
  "confirmado": true,
  "estado_cuadrante": "confirmado"
}
```

---

## 6. `GET /quadrants`

| Campo | Detalle |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/quadrants` |
| **Tag** | `quadrants`, `dna` |
| **Parámetros** | Ninguno |
| **Respuesta exitosa** | `200 OK` — `QuadrantsListResponse` (`{cuadrantes: [...]}` hasta 10 elementos). |
| **Códigos de error** | `503 Service Unavailable` (`ErrorResponse`): falta `DATABASE_URL` en el entorno. |

**Ejemplo de request:**
```bash
curl -s http://127.0.0.1:8000/quadrants
```

**Ejemplo de response (`200 OK`):**
```json
{
  "cuadrantes": [
    {
      "id": "00000000-0000-0000-0000-000000000001",
      "nombre": "Barnard's Star",
      "ra": 269.452075,
      "dec": 4.693365,
      "fov": 2,
      "epoca_a": "DR1",
      "epoca_b": "QR3",
      "estado": "pendiente",
      "es_objeto_prueba": true,
      "tipo_prueba": "movimiento",
      "url_dinamica": "/?ra=17h57m&dec=+4d41m&fov=2"
    }
  ]
}
```

---

## 7. `GET /dna/{objeto}`

| Campo | Detalle |
|---|---|
| **Método** | `GET` |
| **Ruta** | `/dna/{objeto}` |
| **Tag** | `quadrants`, `dna` |
| **Parámetros (path)** | `objeto` *(requerido, string)*: Nombre o slug del objeto (ej. `"Barnard's Star"`). |
| **Respuesta exitosa** | `200 OK` — `CosmicDnaResponse` (`{objeto, bandas, valores, tipo_prueba, descripcion}`). |
| **Códigos de error** | `404 Not Found` (`ErrorResponse`): no existe ADN Cósmico precalculado para el objeto.<br>`422 Unprocessable Content` (`HTTPValidationError`): parámetro inválido. |

**Ejemplo de request:**
```bash
curl -s "http://127.0.0.1:8000/dna/Barnard's%20Star"
```

**Ejemplo de response (`200 OK`):**
```json
{
  "objeto": "Barnard's Star",
  "bandas": [
    "0.75 um",
    "1.10 um",
    "1.65 um",
    "2.20 um",
    "3.40 um",
    "4.10 um",
    "4.80 um"
  ],
  "valores": [0.54, 0.88, 1.0, 0.84, 0.46, 0.34, 0.28],
  "tipo_prueba": "movimiento",
  "descripcion": "Firma visual infrarroja de referencia (enana roja M4V de alto movimiento propio). Uso comparativo visual, no identificacion quimica directa."
}
```
