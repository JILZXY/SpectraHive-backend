<!-- Assisted by Antigravity (SI) — reviewed by Jeshua -->
# SpectraHive Backend (SPHEREx Tracker)

Backend API for **SpectraHive (SPHEREx Tracker)**, a citizen science platform built for the **Planet X and SPHEREx** challenge to help users inspect infrared sky quadrants, blink across two epochs, analyze absolute image differences (`|B - A|`), submit anomaly reports, compare precomputed **Cosmic DNA** visual spectral signatures, and confirm discoveries through cross-validation.

> **Disclosure:** Assisted by Antigravity (SI) — reviewed by Jeshua

---

## Core Workflow & Capabilities

1. **Coordinate Search & Dynamic URLs (`GET /cutout`):** Supports decimal and sexagesimal J2000 coordinates (`RA` in `[0, 360]`, `Dec` in `[-90, +90]`) and fixed field-of-view options (`FOV = 1` or `2`). Serves WCS-centered crops from precomputed IRSA SPHEREx `2040x2040` MEFs (fetched via `astroquery` `Irsa.query_sia` as dated `{slug}_{YYYY-MM-DD}.fits` pairs separated by ~6 months in `t_min` on the same detector when possible) and falls back deterministically to synthetic demo imagery (`fuente: "irsa" | "sintetico"`).
2. **Epoch Blink & Absolute Difference (`POST /diff`):** Aligns Epoch A (earliest MEF date / `DR1`) and Epoch B (~+6 month MEF date / `QR3`) via bounded integer pixel shifts (without arbitrary general reprojection), computes `|Matrix_B - Matrix_A|`, normalizes with 1–99 percentiles into a single infrared false-color palette, applies a robust median/MAD threshold on the raw difference, and classifies candidates (`movimiento`, `lento`, or `brillo`) with human-readable explanations.
3. **Anomaly Reporting & Cross-Validation (`POST /report`, `POST /report/{reporte_id}/validate`):** Enforces domain rules separating moving objects from variable-brightness objects, allows marking clean quadrants (`tipo = "limpio"`), and confirms reports atomically in PostgreSQL/Supabase once `vw_reportes_confirmados` reaches `>= 3` matching votes (`coincide = true`). Simulated demo votes are always tagged (`es_simulado = true`, `etiqueta = "simulado"`).
4. **Fixed Quadrant Queue & Precomputed Cosmic DNA (`GET /quadrants`, `GET /dna/{objeto}`):** Exposes the ordered queue of quadrants and precomputed multi-band infrared signatures formatted as visual barcodes for side-by-side visual comparison (not direct chemical identification without calibration).

---

## Architecture (Clean Architecture)

Dependencies strictly point inward (`API -> Application -> Domain <- Infrastructure`):

```text
spectraHive/
├── app/
│   ├── domain/           # Pure Python entities, Value Objects (RaDec, Fov, Epoch), business rules, Protocols
│   ├── application/      # Use cases (GetCutout, ComputeDiff, CreateReport, ValidateReport, GetCosmicDNA, ListQuadrants)
│   ├── infrastructure/   # Astropy FITS loader, integer alignment, SciPy/Pillow diff renderer, IRSA/synthetic, psycopg v3 repos
│   ├── api/              # FastAPI routers, Pydantic schemas, dependency injection (composition root in deps.py)
│   ├── core/             # Logging & domain-to-HTTP exception mapping
│   ├── config.py         # Environment-driven configuration (fails fast if DATABASE_URL is missing)
│   └── main.py           # FastAPI application entrypoint
├── scripts/              # Offline data prep: build_spectra.py & fetch_cutouts.py (IRSA SIA)
├── data/
│   ├── spectra/          # Precomputed Cosmic DNA JSON signatures
│   └── cutouts/          # Dated 2040x2040 FITS MEFs (gitignored; fetched via fetch_cutouts.py)
├── docs/
│   ├── openapi.json      # Exported OpenAPI 3.1 schema
│   ├── API.md            # Endpoint reference with Barnard's Star examples
│   └── TEST-REPORT.md    # Automated verification report (25/25 passing tests)
├── tests/                # Domain, use-case, and API integration tests (excluded from Docker image)
├── requirements.txt      # Production runtime dependencies
├── requirements-dev.txt  # Development/testing dependencies (includes pytest)
├── supabase-schema.sql   # PostgreSQL / Supabase schema & seed data
├── Dockerfile            # Production runtime image for backend & Render deployment
└── docker-compose.yml    # backend + db-local (postgres:17) services
```

---

## Test Objects Catalog (J2000, FOV 2)

These are the 5 objects the challenge asks to test the tool on, separated strictly into motion vs. brightness groups:

| Object | Test Group (`tipo_prueba`) | RA (J2000) | Dec (J2000) | Dynamic Shortcut |
|---|---|---|---|---|
| **Barnard's Star** | `movimiento` (~10.39"/yr) | `269.452075` (`17h57m48.50s`) | `+4.693365` (`+04°41′36.1″`) | `/?ra=17h57m&dec=+4d41m&fov=2` |
| **WISE 0855-0714** | `movimiento` (~8.15"/yr) | `133.795133` (`08h55m10.83s`) | `-7.245146` (`-07°14′42.5″`) | `/?ra=08h55m&dec=-7d14m&fov=2` |
| **Epsilon Indi B** | `movimiento` (~4.68"/yr) | `331.044147` (`22h04m10.595s`) | `-56.782844` (`-56°46′58.24″`) | `/?ra=22h04m&dec=-56d47m&fov=2` |
| **RW Aurigae** | `brillo` (T Tauri) | `76.956067` (`05h07m49.456s`) | `+30.401326` (`+30°24′04.77″`) | `/?ra=05h07m&dec=+30d24m&fov=2` |
| **R Draconis** | `brillo` (Mira variable) | `248.167625` (`16h32m40.23s`) | `+66.754972` (`+66°45′17.9″`) | `/?ra=16h32m&dec=+66d45m&fov=2` |

---

## API Endpoints & Documentation

Once the server is running on port `8000`:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON:** `http://127.0.0.1:8000/openapi.json` (static export at [`docs/openapi.json`](./docs/openapi.json))
- **Markdown Reference:** [`docs/API.md`](./docs/API.md)
- **Test Report:** [`docs/TEST-REPORT.md`](./docs/TEST-REPORT.md)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health & database configuration check (Render warm-up) |
| `GET` | `/cutout` | Returns infrared cutout (`json` base64 or `png`) for J2000 `ra`, `dec`, `fov`, `epoca` |
| `POST` | `/diff` | Aligns Epoch A & B, computes `\|B - A\|`, threshold, and candidate classifications |
| `POST` | `/report` | Persists an anomaly (`movimiento` / `brillo`) or `limpio` report |
| `POST` | `/report/{reporte_id}/validate` | Records a cross-validation vote; confirms quadrant at `>= 3` matching votes |
| `GET` | `/quadrants` | Lists the ordered fixed queue of up to 10 quadrants |
| `GET` | `/dna/{objeto}` | Returns precomputed Cosmic DNA visual signature for a test object |

---

## Environment Variables

Copy [`.env.example`](./.env.example) to `.env` (never commit `.env` to Git):

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes (for DB routes) | PostgreSQL connection string. Local: `postgresql://spectrahive:spectrahive_local_dev@db-local:5432/spectrahive`. Production (Render): Supabase Supavisor transaction pooler string (port `6543`). Missing `DATABASE_URL` raises an explicit `RuntimeError` / `503`. |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (defaults to `http://localhost:5173,http://localhost:3000`; set your Vercel frontend URL in production). |
| `DATA_DIR` | No | Path to precomputed `spectra/` and `cutouts/` directory (defaults to `data`). |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Optional | Reference variables if needed outside direct `psycopg` connection. Never expose service or anon keys in frontend code. |

---

## Getting Started

### Option A: Docker Compose (Recommended Standard Environment)

Docker Compose starts `db-local` (`postgres:17`, auto-initialized with [`supabase-schema.sql`](./supabase-schema.sql)) and `backend` (`python:3.12-slim`):

1. **Create your local `.env` from `.env.example`:**
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

2. **Build and start all services:**
   ```bash
   docker compose up --build
   ```
   The API will be available at `http://localhost:8000` (Swagger UI at `http://localhost:8000/docs`).

3. **Stop and clean up containers:**
   ```bash
   docker compose down
   ```

> **Note:** The production `Dockerfile` excludes `pytest` and `tests/` to keep the runtime image lean. Run the automated test suite from the local virtual environment using `requirements-dev.txt` (Option B).

### Option B: Local Python Virtual Environment (`.venv`)

1. **Create and activate a virtual environment (Python 3.12+ recommended):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(On Linux/macOS: `source .venv/bin/activate`)*

2. **Install dependencies:**
   - Runtime only: `pip install -r requirements.txt`
   - Development & tests (`pytest`):
     ```bash
     pip install -r requirements-dev.txt
     ```

3. **Prepare offline precomputed data (`data/spectra/` and `data/cutouts/`):**
   ```bash
   python scripts/build_spectra.py
   python scripts/fetch_cutouts.py --offline-fallback
   ```

4. **Configure environment variables:**
   Copy `.env.example` to `.env` and point `DATABASE_URL` to your running PostgreSQL instance (`localhost:5432` or Supabase pooler).

5. **Run the API server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Run tests:**
   ```bash
   pytest -v
   ```

---

## Production Deployment Notes

- **Backend Hosting:** Deploy via [`Dockerfile`](./Dockerfile) on Render (recommended region: **Oregon / `us-west-2`** to stay co-located with the Supabase PostgreSQL project).
- **Database Schema:** [`supabase-schema.sql`](./supabase-schema.sql) serves as the schema source of truth and backup (`cuadrantes`, `reportes`, `validaciones`, `vw_reportes_confirmados`, and the 5 seeded test objects). Schema updates on Supabase must be applied via the Supabase SQL Editor.

---

## Data Sources & Stack Acknowledgments

- **Astronomical Data & Tools:** NASA/IPAC IRSA SPHEREx (DR1 / QR3 via SIAv2), Gaia DR3, Astropy, Astroquery, NumPy, SciPy, Pillow.
- **Backend & Persistence:** FastAPI, Uvicorn, Pydantic, `psycopg` (v3) + `psycopg_pool`, PostgreSQL / Supabase, Docker.
