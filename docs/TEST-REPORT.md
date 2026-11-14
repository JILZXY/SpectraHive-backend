<!-- Assisted by Antigravity (SI) — reviewed by Jeshua -->
# SpectraHive Backend — Reporte de Pruebas (Test Report)

## 1. Entorno de ejecución y comando

| Campo | Valor |
| :--- | :--- |
| **Entorno** | Local (`.venv` Python virtualenv; `tests/` excluido de la imagen Docker de producción en `Dockerfile` / `.dockerignore`) |
| **Python** | `3.15.2` |
| **Sistema Operativo** | `Windows-11-10.0.26300-SP0` |
| **Pytest / Pluggy** | `pytest 9.2.0`, `pluggy 1.7.0`, `anyio 4.16.0` |
| **Comando exacto** | `.\.venv\Scripts\python.exe -m pytest -v` |
| **Resultado global** | `25 passed, 1 warning in 2.24s` |
| **Veredicto general** | **APTO** |

---

## 2. Tabla de las 25 pruebas ejecutadas

| # | Prueba (`nodeid`) | Módulo | Qué verifica (`RF` / `RN`) | Resultado | Veredicto |
| :-: | :--- | :--- | :--- | :---: | :---: |
| 1 | `tests/test_api.py::test_api_endpoints_end_to_end` | API (`TestClient`) | Flujo completo: `GET /health`, `GET /cutout` (JSON y PNG, errores `400` en RA/FOV), `POST /diff`, `GET /quadrants`, `GET /dna/{objeto}`, `POST /report` (incluye rechazo cruzado `400` RN-02) y 3 votos de `POST /report/{id}/validate` hasta `confirmado` (RF-01..RF-15, §6). | `PASSED` | **APTO** |
| 2 | `tests/test_api.py::test_openapi_and_swagger_ui_routes` | API (`TestClient`) | Disponibilidad de `/openapi.json`, `/docs` (`SwaggerUIBundle`), `/redoc`, presencia de `/cutout`, `/diff`, `/report`, `/health` y ejemplos reales de Barnard's Star (`ra=269.452075`, `dec=4.693365`, `fov=2`). | `PASSED` | **APTO** |
| 3 | `tests/test_domain.py::test_radec_valid_decimal_and_sexagesimal` | Dominio | Parseo decimal y sexagesimal de coordenadas J2000 (atajos RF-03 / §5 para Barnard `17h57m +4d41m` y WISE 0855 `08h55m -7d14m`). | `PASSED` | **APTO** |
| 4 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[-0.1-0.0]` | Dominio | Rechazo de RA negativa (`-0.1`) mediante `InvalidCoordinatesError` (RF-01). | `PASSED` | **APTO** |
| 5 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[360.1-0.0]` | Dominio | Rechazo de RA > 360° (`360.1`) mediante `InvalidCoordinatesError` (RF-01). | `PASSED` | **APTO** |
| 6 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[100.0--90.1]` | Dominio | Rechazo de Dec < -90° (`-90.1`) mediante `InvalidCoordinatesError` (RF-01). | `PASSED` | **APTO** |
| 7 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[100.0-90.1]` | Dominio | Rechazo de Dec > +90° (`90.1`) mediante `InvalidCoordinatesError` (RF-01). | `PASSED` | **APTO** |
| 8 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[25h00m-+10d00m]` | Dominio | Rechazo de RA sexagesimal fuera de 24h (`25h00m`) (RF-01). | `PASSED` | **APTO** |
| 9 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[invalid-0.0]` | Dominio | Rechazo de cadena no parseable (`"invalid"`) (RF-01). | `PASSED` | **APTO** |
| 10 | `tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[-0.0]` | Dominio | Rechazo de cadena vacía en RA (`""`) (RF-01). | `PASSED` | **APTO** |
| 11 | `tests/test_domain.py::test_radec_proper_motion_propagation_rn05` | Dominio | Propagación de movimiento propio de Barnard's Star a ~2026.9 (~4.66 arcmin en 26.9 años) (RN-05). | `PASSED` | **APTO** |
| 12 | `tests/test_domain.py::test_fov_only_allows_1_and_2` | Dominio | Validación estricta de `fov ∈ {1, 2}` y rechazo de `0, 3, -1, 1.5, True, "abc"` con `InvalidFovError` (RF-02). | `PASSED` | **APTO** |
| 13 | `tests/test_domain.py::test_epoch_aliases` | Dominio | Equivalencia entre alias `A`/`B` y etiquetas `DR1`/`QR3` en `Epoch`. | `PASSED` | **APTO** |
| 14 | `tests/test_domain.py::test_validate_report_type_rn02_rn03_rf11` | Dominio | Separación estricta entre grupos `movimiento` y `brillo`, permiso de `limpio` y rechazo con `ReportTypeMismatchError` / `InvalidReportTypeError` (RN-02, RN-03, RF-11). | `PASSED` | **APTO** |
| 15 | `tests/test_domain.py::test_confirm_report_requires_3_votes_rf12_rn06` | Dominio | Regla de quórum exacto de 3 votos `coincide=True` para confirmar reporte y pasar cuadrante de `pendiente` a `confirmado` (RF-12, RN-06, RN-08). | `PASSED` | **APTO** |
| 16 | `tests/test_domain.py::test_classify_candidate_and_simulated_label` | Dominio | Clasificación de candidatos (`movimiento`, `lento`, `brillo`) y etiquetado obligatorio `"simulado"` cuando `es_simulado=True` (RF-09, RF-13). | `PASSED` | **APTO** |
| 17 | `tests/test_domain.py::test_clean_architecture_dependency_rule` | Arquitectura | Regla de dependencia de Clean Architecture: `domain/` y `application/` sin imports de FastAPI, Astropy, Psycopg, SciPy o PIL. | `PASSED` | **APTO** |
| 18 | `tests/test_use_cases.py::test_create_report_and_cross_validation_flow` | Casos de uso | Flujo `CreateReport` -> 3 llamadas a `ValidateReport` confirmando el reporte en el voto #3 con transición del cuadrante a `confirmado` (RF-10, RF-12, RF-13, RN-06, RN-08). | `PASSED` | **APTO** |
| 19 | `tests/test_use_cases.py::test_create_report_rejects_wrong_group_and_clean_validation` | Casos de uso | Rechazo de `movimiento` en RW Aurigae (`brillo`) y prohibición de validar un reporte `limpio` (RN-02, RN-03, RF-11). | `PASSED` | **APTO** |
| 20 | `tests/test_use_cases.py::test_compute_diff_barnard_and_rw_aurigae` | Casos de uso + FITS | Resta `\|B - A\|`, umbral robusto y clasificación real sobre el proveedor sintético: Barnard (`movimiento`), WISE 0855 (`movimiento`), RW Aurigae (`brillo`), R Draconis (`brillo`) (RF-08, RF-09, RN-02, RN-03). | `PASSED` | **APTO** |
| 21 | `tests/test_use_cases.py::test_get_cutout_reads_irsa_fits_and_falls_back` | Casos de uso + FITS | Lectura de FITS con cabecera `SOURCE=IRSA` desde disco (`fuente="irsa"`) y fallback automático a sintético (`fuente="sintetico"`) si falta una época (RF-16). | `PASSED` | **APTO** |
| 22 | `tests/test_use_cases.py::test_cosmic_dna_and_list_quadrants` | Casos de uso | Carga de ADN Cósmico precalculado de 7 bandas (`GetCosmicDNA`), error `ResourceNotFoundError` en objeto inexistente y cola de 5 objetos en `ListQuadrants` (RF-05, RF-14, RF-15). | `PASSED` | **APTO** |
| 23 | `tests/test_use_cases.py::test_database_url_missing_fails_explicitly` | Config / Infra DB | Fallo explícito (`DatabaseConfigError` / `RuntimeError`) cuando falta `DATABASE_URL` en el entorno sin usar credenciales por defecto. | `PASSED` | **APTO** |
| 24 | `tests/test_use_cases.py::test_sia_select_epoch_pair_prefers_6_months_and_same_detector_including_dr1_only` | Infra IRSA SIA | Selector SIA (`select_epoch_pair`): prioriza ~6 meses (`120..245` días) en `t_min` y mismo detector (`D3`), incluso cuando todas las observaciones provienen solo de `spherex_dr1` (caso WISE 0855-0714). | `PASSED` | **APTO** |
| 25 | `tests/test_use_cases.py::test_precomputed_provider_reads_dated_irsa_mef_cutout` | Infra FITS / IRSA | Lectura de MEFs fechados `{slug}_{YYYY-MM-DD}.fits` en `PrecomputedCutoutProvider` con cabecera `SOURCE=IRSA` y extracción centrada de cutout devolviendo `fuente="irsa"` para épocas A y B (RF-16). | `PASSED` | **APTO** |

---

## 3. Salida íntegra de la ejecución (`pytest -v`)

```text
============================= test session starts =============================
platform win32 -- Python 3.15.2, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\sasos\Documents\Tarea\spectraHive\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\sasos\Documents\Tarea\spectraHive
plugins: anyio-4.16.0
collecting ... collected 25 items

tests/test_api.py::test_api_endpoints_end_to_end PASSED                  [  4%]
tests/test_api.py::test_openapi_and_swagger_ui_routes PASSED             [  8%]
tests/test_domain.py::test_radec_valid_decimal_and_sexagesimal PASSED    [ 12%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[-0.1-0.0] PASSED [ 16%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[360.1-0.0] PASSED [ 20%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[100.0--90.1] PASSED [ 24%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[100.0-90.1] PASSED [ 28%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[25h00m-+10d00m] PASSED [ 32%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[invalid-0.0] PASSED [ 36%]
tests/test_domain.py::test_radec_rejects_out_of_range_and_invalid[-0.0] PASSED [ 40%]
tests/test_domain.py::test_radec_proper_motion_propagation_rn05 PASSED   [ 44%]
tests/test_domain.py::test_fov_only_allows_1_and_2 PASSED                [ 48%]
tests/test_domain.py::test_epoch_aliases PASSED                          [ 52%]
tests/test_domain.py::test_validate_report_type_rn02_rn03_rf11 PASSED    [ 56%]
tests/test_domain.py::test_confirm_report_requires_3_votes_rf12_rn06 PASSED [ 60%]
tests/test_domain.py::test_classify_candidate_and_simulated_label PASSED [ 64%]
tests/test_domain.py::test_clean_architecture_dependency_rule PASSED     [ 68%]
tests/test_use_cases.py::test_create_report_and_cross_validation_flow PASSED [ 72%]
tests/test_use_cases.py::test_create_report_rejects_wrong_group_and_clean_validation PASSED [ 76%]
tests/test_use_cases.py::test_compute_diff_barnard_and_rw_aurigae PASSED [ 80%]
tests/test_use_cases.py::test_get_cutout_reads_irsa_fits_and_falls_back PASSED [ 84%]
tests/test_use_cases.py::test_cosmic_dna_and_list_quadrants PASSED       [ 88%]
tests/test_use_cases.py::test_database_url_missing_fails_explicitly PASSED [ 92%]
tests/test_use_cases.py::test_sia_select_epoch_pair_prefers_6_months_and_same_detector_including_dr1_only PASSED [ 96%]
tests/test_use_cases.py::test_precomputed_provider_reads_dated_irsa_mef_cutout PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\sasos\Documents\Tarea\spectraHive\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 25 passed, 1 warning in 2.24s ========================
```
