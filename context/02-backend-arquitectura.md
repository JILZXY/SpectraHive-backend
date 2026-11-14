# SpectraHive — Arquitectura del backend (FastAPI)

> Rol 02 — Backend + Datos. Jeshua.
> Repo: https://github.com/JILZXY/SpectraHive-backend.git
> Lee primero `context/00-contexto-general.md` (RF-01…RF-17, RN-01…RN-14) y
> `context/02-backend-datos.md`. Este archivo define **cómo** se organiza el
> código, no **qué** hace el producto: no cambia ningún RF, RN, contrato ni
> el stack. Si un cambio aquí afectara a un contrato o al alcance, aplica
> RN-14 (avisar al humano, esperar acuerdo del equipo).

## 0. Nota sobre "CoVe"

**CoVe = Chain of Verification (cadena de verificación):** técnica para
verificar que una propuesta realmente sea viable, generando preguntas de
verificación, respondiéndolas de forma independiente contra los requisitos
y corrigiendo la propuesta con lo que se encuentre. Este documento se sometió
a CoVe en §11 (2026-11-14 ~13:35): la arquitectura es viable, pero la
verificación encontró 4 huecos reales que ya están corregidos aquí
(andamiaje excesivo para 48 h, `/diff` bloqueante, falta el pipeline de
preparación de datos, y doble fuente de verdad en la confirmación).
La arquitectura base es Clean Architecture (capas concéntricas / hexagonal).

## 1. Idea en una frase

**El backend es un monolito FastAPI organizado en capas concéntricas, con el
dominio puro en el centro y todo lo externo (HTTP, FITS, IRSA, Supabase)
como adaptadores intercambiables.** Hoy corre con 3 endpoints y adaptadores
simples; mañana cada cosa descartada del MVP entra como un adaptador nuevo
sin reescribir el dominio ni los contratos.

## 2. Capas y regla de dependencia

```
┌─────────────────────────────────────────────────┐
│ API (routers, schemas Pydantic, Depends)        │  ← FastAPI vive solo aquí
├─────────────────────────────────────────────────┤
│ Aplicación (casos de uso / servicios)           │  ← orquesta, no calcula
├─────────────────────────────────────────────────┤
│ Dominio (entidades, reglas RN, puertos)         │  ← Python puro, sin I/O
├─────────────────────────────────────────────────┤
│ Infraestructura (adaptadores)                   │  ← Astropy, IRSA, Supabase
└─────────────────────────────────────────────────┘
```

**Regla de oro:** las dependencias apuntan hacia adentro. El dominio no
importa nada de `fastapi`, `astropy`, `supabase` ni `sqlalchemy`. La
infraestructura importa al dominio, nunca al revés. La API importa a la
aplicación y al dominio, nunca a la infraestructura directamente: todo lo
externo llega por inyección de dependencias (`api/deps.py` / `main.py`,
la *composition root*).

| Capa | Contiene | NO contiene |
|---|---|---|
| API | Routers, schemas de request/response, manejo de errores HTTP, CORS, auth (cuando exista) | Lógica de negocio, Astropy, SQL |
| Aplicación | Casos de uso: `GetCutout`, `ComputeDiff`, `CreateReport`, `ValidateReport`, `GetCosmicDNA`, `ListQuadrants` | FITS, HTTP, SQL |
| Dominio | Entidades, value objects, reglas RN-01…RN-14, puertos (`Protocol`) | I/O, frameworks, librerías externas |
| Infraestructura | Adaptadores FITS/IRSA/Supabase/cache, cliente TAP, fallback sintético | Reglas de negocio (solo las ejecuta) |

## 3. Dominio (el centro, Python puro)

### 3.1 Entidades

- `Quadrant`: `id`, `nombre`, `ra`, `dec` (J2000), `fov`, `epoca_a`,
  `epoca_b`, `estado ∈ {pendiente, confirmado, descartado}`,
  `es_objeto_prueba`, `tipo_prueba ∈ {movimiento, brillo}`.
- `Report`: `id`, `cuadrante_id`, `ra`, `dec`, `tipo ∈ {movimiento, brillo, limpio}`.
- `Validation`: `id`, `reporte_id`, `coincide`, `es_simulado`.
- `Candidate`: `ra`, `dec`, `valor`, `motivo` (salida de `/diff`).
- `SpectralSignature`: `objeto`, `bandas`, `valores` (ADN Cósmico).

### 3.2 Value objects

- `RaDec`: valida rangos (RA 0–360°, Dec −90…+90°), guarda grados J2000.
  Rechaza coordenadas fuera de rango (RF-01). La propagación J2000 → 2026.9
  vive aquí como función pura (`propagate(pm_ra, pm_dec, años)`), sin I/O.
- `Fov`: solo 1 o 2 (RF-02).
- `Epoch`: una época es un identificador (`"DR1"`, `"QR3"`, …), no un
  archivo. Hoy solo hay A y B; mañana la lista crece sin tocar el dominio.

### 3.3 Reglas de negocio en código (RN como funciones, no como comentarios)

- `validate_report_type(cuadrante, tipo)`: `tipo` debe coincidir con
  `cuadrante.tipo_prueba`, salvo `limpio` (RN-02/RN-03). Un reporte
  `movimiento` para RW Aurigae o R Draconis es inválido.
- `confirm_report(validaciones)`: confirmado solo con ≥ 3 validaciones
  `coincide = true` sobre el mismo `reporte_id` (RF-12, RN-08).
- `classify_candidate(desplazamiento, cambio_brillo)`: `movimiento` /
  `brillo` / `lento` (candidato tipo Planet X: desplazamiento pequeño pero
  distinto de cero entre épocas; el umbral de "lento" es un parámetro del
  dominio, no un número mágico en el router).
- `simulated_votes_must_be_labelled`: todo voto simulado lleva
  `es_simulado = true` y la API lo devuelve tal cual (RF-13).

### 3.4 Puertos (interfaces, `typing.Protocol`)

El dominio define lo que necesita; la infraestructura lo implementa:

```python
class CutoutProvider(Protocol):
    def get_cutout(self, ra_dec: RaDec, fov: Fov, epoch: Epoch) -> Cutout: ...

class AlignmentService(Protocol):
    def align(self, a: Image, b: Image) -> tuple[Image, Image]: ...

class SpectralProvider(Protocol):
    def signature(self, objeto: str) -> SpectralSignature: ...

class QuadrantRepository(Protocol):
    def get(self, id: str) -> Quadrant: ...
    def list_queue(self) -> list[Quadrant]: ...

class ReportRepository(Protocol):
    def save(self, report: Report) -> Report: ...
    def validations_for(self, reporte_id: str) -> list[Validation]: ...
```

Hoy cada puerto tiene **un** adaptador. Escalar es **añadir** un adaptador,
no reescribir el puerto.

## 4. Aplicación (casos de uso)

Un caso de uso = un endpoint (o parte de él). Orquesta puertos, no calcula:

- `GetCutout(ra, dec, fov)` → valida `RaDec`/`Fov` → `CutoutProvider`
  (IRSA precalculado → fallback sintético) → devuelve imagen + JSON
  `{ra, dec, fov, epoca, fuente: "irsa" | "sintetico"}` (RF-16).
- `ComputeDiff(cuadrante_id, epoca_a, epoca_b)` → carga A y B →
  `AlignmentService.align` → resta `|B−A|` con percentiles 1–99 →
  umbral → `classify_candidate` por candidato → `{umbral, candidatos}`.
- `CreateReport(cuadrante_id, ra, dec, tipo)` → `validate_report_type` →
  guarda en `ReportRepository` → `{reporte_id, estado}`.
- `ValidateReport(reporte_id, coincide, es_simulado)` → guarda validación
  → si hay 3 coincidencias, marca el cuadrante `confirmado`.
- `GetCosmicDNA(objeto)` → `SpectralProvider.signature` (precalculado).

Ningún caso de uso importa `astropy`, `supabase` ni `fastapi`.

## 5. Infraestructura (adaptadores)

| Puerto | Adaptador MVP (hoy) | Adaptador futuro (sin tocar dominio) |
|---|---|---|
| `CutoutProvider` | `PrecomputedCutoutProvider` (FITS en disco, leídos con Astropy) + `SyntheticCutoutProvider` (fallback) | `IrsaCutoutProvider` (descarga en vivo), `HipsCutoutProvider` (panorama HiPS propio) |
| `AlignmentService` | `IntegerShiftAlignment` (desplazamiento entero de píxeles) | `WcsReprojectionAlignment` (reproyección WCS general) |
| `SpectralProvider` | `PrecomputedSpectralProvider` (JSON por objeto, 6–8 bandas) | `LiveSpectralExtractor` (102 bandas en vivo con Astropy) |
| `QuadrantRepository` | `SupabaseQuadrantRepository` (tabla `cuadrantes`, cola fija de 10) | `RandomGridQuadrantProvider` (cuadrícula aleatoria infinita) |
| `ReportRepository` | `SupabaseReportRepository` (tablas `reportes`, `validaciones`) | — (misma tabla, más reglas) |
| (nuevo) `TapClient` | TAP acotado solo para localizar cutouts de prueba | `GenericTapClient` (TAP genérico en vivo) |
| (nuevo) `PositionProvider` | — | `MostPositionProvider` (posiciones esperadas Planet X) |
| (nuevo) `AuthProvider` | — (sin usuarios en MVP) | Supabase Auth + entidades `User`/`Rol` en dominio + RLS en Supabase (un adaptador solo NO basta: hacen falta modelo de usuario y permisos) |
| (nuevo) `JobQueue` | `BackgroundTasks` de FastAPI (hoy, dentro del request) | Cola real (RQ/Celery) para `/diff` pesado |

**Caché:** `CutoutCache` es otro puerto. Hoy: disco local (`data/cache/`).
Mañana: Redis, sin cambiar ningún caso de uso.

## 6. Estructura de carpetas del repo

```
SpectraHive-backend/
├── context/                        # ya existe: contexto del proyecto
│   ├── 00-contexto-general.md     # RF/RN, contratos, catálogo (fuente única)
│   ├── 02-backend-datos.md        # rol 02
│   └── ARCHITECTURE.md            # este archivo (copia aquí)
├── app/
│   ├── main.py                     # composition root: crea la app, inyecta adaptadores
│   ├── config.py                   # Settings (.env, nunca commiteado)
│   ├── api/
│   │   ├── deps.py                 # Depends: get_cutout_use_case(), etc.
│   │   └── v1/
│   │       ├── cutouts.py          # GET /cutout
│   │       ├── diffs.py            # POST /diff
│   │       ├── reports.py          # POST /report (+ validaciones)
│   │       └── quadrants.py        # GET /quadrants, GET /dna (ADN Cósmico)
│   ├── application/
│   │   ├── use_cases.py            # GetCutout, ComputeDiff, CreateReport, ...
│   │   └── dto.py                  # dataclasses entre capas
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py        # RaDec, Fov, Epoch
│   │   ├── rules.py                # RN como funciones
│   │   └── ports.py                # Protocols
│   ├── infrastructure/
│   │   ├── fits/                   # loader Astropy, false colour, resta
│   │   │   ├── loader.py
│   │   │   ├── alignment.py        # IntegerShiftAlignment
│   │   │   └── rendering.py        # percentiles 1-99, umbral
│   │   ├── irsa/
│   │   │   ├── client.py           # descarga / TAP acotado
│   │   │   └── precomputed.py      # PrecomputedCutoutProvider
│   │   ├── synthetic/
│   │   │   └── fallback.py         # SyntheticCutoutProvider (demo 2026-11-12)
│   │   ├── supabase/
│   │   │   ├── client.py
│   │   │   └── repositories.py     # Quadrant/ReportRepository
│   │   └── cache/
│   │       └── disk_cache.py
│   └── core/
│       ├── errors.py               # errores de dominio → HTTP
│       └── logging.py
├── tests/
│   ├── test_domain.py              # reglas RN puras, sin I/O (los más valiosos)
│   ├── test_use_cases.py           # casos de uso con puertos falsos (fakes)
│   └── test_api.py                 # e2e: /cutout, /diff, /report contra db-local
├── scripts/                        # pipeline OFFLINE de preparación de datos (CoVe V4)
│   ├── fetch_cutouts.py            # descarga cutouts IRSA DR1/QR3 → data/cutouts/
│   └── build_spectra.py            # construye el ADN precalculado → data/spectra/
├── data/
│   ├── cutouts/                    # FITS precalculados (.gitignore, no al repo)
│   └── spectra/                    # ADN precalculado (JSON por objeto)
├── Dockerfile
├── docker-compose.yml              # backend + db-local (Postgres de pruebas)
├── requirements.txt                # fastapi, uvicorn, astropy, numpy, scipy, supabase
├── .env.example                    # claves SIN valores reales
├── .gitignore                      # .env, data/cutouts/*.fits, __pycache__
└── README.md                       # cómo levantar: docker compose up --build
```

**Regla de archivos:** si un módulo importa algo de una capa exterior, está
mal ubicado. `domain/` no importa `fastapi`, `astropy` ni `supabase`; se
puede verificar con un grep en CI o a mano antes de cada commit.

## 7. Flujo de un request (ejemplo: POST /diff)

**Los endpoints de cálculo (`/cutout`, `/diff`) se declaran con `def`
síncrono, no `async def` (CoVe V3):** Astropy/NumPy es trabajo CPU-bound y
un `async def` lo ejecutaría en el event loop, bloqueando todos los demás
requests. Con `def`, FastAPI lo corre en su threadpool. Alternativa:
`run_in_executor`. Además, los cutouts van acotados en tamaño (FOV 1/2) para
no superar los timeouts de Render.

```
Cliente (Vite)
  → api/v1/diffs.py: valida el JSON con Pydantic, nada más
  → application.ComputeDiff: pide A y B a CutoutProvider
  → infrastructure.irsa.PrecomputedCutoutProvider: lee FITS con Astropy
      (si falla → SyntheticCutoutProvider, fuente="sintetico")
  → infrastructure.fits.alignment.IntegerShiftAlignment: alinea A y B
  → application.ComputeDiff: resta |B−A|, percentiles 1–99, umbral
  → domain.rules.classify_candidate: movimiento / brillo / lento
  → api/v1/diffs.py: devuelve imagen + {umbral, candidatos}
```

Si mañana la alineación pasa a WCS, solo cambia el adaptador que se inyecta
en `main.py`. El router, el caso de uso y el dominio no se tocan.

## 8. Qué NO construir hoy (aunque la arquitectura ya lo prevé)

- Microservicios: el monolito con 3 endpoints es la decisión correcta para
  48 h. La separación en puertos ya permite extraer un servicio después
  (por ejemplo, un worker de `/diff`) sin reescribir el dominio.
- Autenticación / usuarios / leaderboard: el puerto `AuthProvider` existe
  como hueco, no como código.
- TAP genérico, HiPS propio, WCS general, 102 bandas en vivo, cuadrícula
  aleatoria: son adaptadores futuros, no trabajo de hoy. Cada uno se añade
  cuando el equipo lo acuerde (RN-14).
- Caché Redis, cola de trabajos, observabilidad completa: fuera del MVP.

## 9. Orden de construcción (rol 02, hoy sábado)

**Fase 1 — Clean-lite (hasta el checkpoint de las 20:00):** no se crean los
~30 archivos del árbol de §6 de golpe. Se empieza con ~12 archivos:
`main.py`, `config.py`, `api/deps.py` + 3 routers, `application/use_cases.py`,
`domain/entities.py` + `value_objects.py` + `rules.py` + `ports.py`, y en
infraestructura un solo `adapters.py` por fuente (fits, irsa, supabase) que
se divide solo cuando crezca. La separación por capas y la regla de
dependencia se respetan desde el minuto uno; la granularidad de archivos,
no. Si a las 20:00 no hay blink real, el andamiaje sobró.

0. **Preparación de datos (scripts/, antes de programar la API):** correr
   `fetch_cutouts.py` (cutouts IRSA de los 5 objetos, 2 épocas) y
   `build_spectra.py` (ADN precalculado). Sin esto, `PrecomputedCutoutProvider`
   y `PrecomputedSpectralProvider` no tienen nada que servir.
1. Esqueleto: `app/domain/` + `app/api/` + `main.py` con `/health`, y
   `docker compose up --build` funcionando.
2. `GetCutout` con `PrecomputedCutoutProvider` + fallback sintético.
   Checkpoint: Barnard real por `/cutout`.
3. `ComputeDiff` con `IntegerShiftAlignment` + resta + umbral.
   Checkpoint: `|B−A|` con 2 puntos para Barnard.
4. `CreateReport` + `ValidateReport` contra Supabase (vía `db-local`
   primero, RN-13).
5. `GetCosmicDNA` precalculado.
6. Tests: primero `test_domain.py` (reglas RN), luego e2e de los 3
   endpoints. `docker compose run backend pytest`.

## 10. Git (repo ya creado, vacío)

- `main`: lo que está desplegado en Render. No se commitea directo.
- Ramas por caso de uso: `feat/cutout`, `feat/diff`, `feat/report`,
  `feat/dna`. Merge a `main` solo con el endpoint probado en local.
- `context/` se commitea (son los MD del proyecto). `.env` y
  `data/cutouts/*.fits` nunca se commitean (van en `.gitignore`).
- Cada commit que toque un contrato o el alcance es cambio sustancial
  (RN-14): avisar antes de mergear.

## 11. Chain of Verification (CoVe) — ¿es viable esta arquitectura?

Método: se generaron preguntas de verificación contra los requisitos
(RF/RN, contratos §6 del 00, stack, 48 h, 1 dev backend, Docker/Render,
Supabase, IRSA) y se respondieron de forma independiente. Veredicto global:
**viable, con 4 correcciones aplicadas** (ya están en este documento).

| # | Pregunta de verificación | Veredicto |
|---|---|---|
| V1 | ¿Los 3 endpoints con sus contratos exactos se pueden implementar en 48 h con esta estructura? | ⚠ Sí, pero el andamiaje completo (~30 archivos) se come el sábado. **Corrección:** Fase 1 Clean-lite con ~12 archivos (§9). |
| V2 | ¿La regla de dependencia (dominio puro) se sostiene con FITS/NumPy? | ⚠ Parcial. Un array NumPy en el dominio es una fuga pragmática pero contenida: se define `Image` como value object (array + metadatos) y se prohíbe `astropy` en `domain/`. Aceptable. |
| V3 | ¿`/diff` (Astropy/NumPy, CPU-bound) bloquea el event loop o supera timeouts de Render? | ✗ Riesgo real con `async def`. **Corrección:** endpoints de cálculo con `def` síncrono (threadpool) o `run_in_executor`, cutouts acotados (§7). |
| V4 | ¿De dónde salen los cutouts precalculados y el ADN precalculado? ¿Quién los produce? | ✗ Hueco: ningún componente los generaba. **Corrección:** `scripts/` con `fetch_cutouts.py` y `build_spectra.py`, paso 0 del orden (§6, §9). |
| V5 | ¿La confirmación con 3 votos tiene una sola fuente de verdad? | ⚠ No: la vista `vw_reportes_confirmados` y la regla `confirm_report` duplicaban la lógica. **Corrección:** la vista es la fuente de verdad para lectura; la regla de dominio decide el cambio de estado consultando el conteo, no reimplementándolo. Además, RN-02 se refuerza con `CHECK` en la BD (segunda línea de defensa si alguien escribe reportes directo a Supabase). |
| V6 | ¿La arquitectura resuelve el riesgo de alineación sub-píxel? | ⚠ No, solo lo aísla en un adaptador. **Corrección:** verificación temprana obligatoria con pares reales IRSA en el checkpoint de las 20:00; plan B: usar imágenes ya alineadas (Aladin/HiPS) como fuente si el par no alinea. La arquitectura no convierte un riesgo de datos en un problema resuelto. |
| V7 | ¿Docker/Render aguantan: tamaño de imagen, cold start, CORS? | ⚠ Parcial. **Correcciones:** `.dockerignore` y FITS pequeños en la imagen; `GET /health` para warm-up (Astropy tarda en importar, Render free se duerme); CORS con el origen de Vercel explícito por variable de entorno, no `*`. |
| V8 | ¿Usuarios/perfiles/leaderboard es solo añadir `AuthProvider`? | ✗ No. **Corrección:** hacen falta entidades `User`/`Rol` en el dominio y RLS en Supabase (§5). |
| V9 | ¿Contradice la propuesta que los reportes pasen por FastAPI si dice "Supabase directo para CRUD"? | ✓ Con matiz. El contrato exige `POST /report` en FastAPI, así que pasar por el dominio es correcto: ahí vive la validación RN-02. "Supabase directo" vale para lecturas simples; la escritura de reportes no debe saltarse la validación (ver V5, `CHECK`). |
| V10 | ¿El frontend o los otros roles dependen de algo de esta arquitectura? | ✓ No. Los contratos (§6 del 00) no cambian; la arquitectura es interna del backend. |
| V11 | ¿Cada cosa descartada del MVP tiene un punto de entrada sin reescribir el dominio? | ✓ Sí: HiPS, TAP genérico, WCS, 102 bandas en vivo, cuadrícula aleatoria, MOST y cola de trabajos mapean a adaptadores (§5). Usuarios es la excepción (V8). |

**Lo que CoVe NO pudo verificar (queda como riesgo abierto):** que IRSA
entregue los cutouts DR1/QR3 de los 5 objetos en el formato esperado y que
los pares A/B vengan alineados a menos de un píxel. Eso solo se verifica
corriendo `scripts/fetch_cutouts.py` y el checkpoint de Barnard. Si eso
falla, ninguna arquitectura lo arregla: se usa el fallback sintético y se
declara como límite honesto en la entrega.
