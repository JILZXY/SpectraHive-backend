# SpectraHive — Requisitos funcionales y reglas de negocio (fuente única de verdad)

> Léelo primero, junto con tu archivo de rol (01–04). Este archivo define el esquema
> común del proyecto. **Si algo choca con este archivo, este archivo manda** — por
> encima de la propuesta, del kit y de lo que te diga tu IA.
> La propuesta corregida (9 pp., en español) es guía de desarrollo, no es el entregable.
> Propuesta: `../spherex-tracker-propuesta-corregida/spherex-tracker-propuesta-corregida.pdf`
> Kit día 1: `../spectrahive-starter-kit/README-dia-1.md` y `supabase-schema.sql`

## 1. Qué es SpectraHive (una frase)

Plataforma web de ciencia ciudadana para descubrir objetos infrarrojos en datos de
SPHEREx: el usuario revisa un cuadrante, hace Blink entre dos épocas, marca si está
limpio o reporta una anomalía, y la anomalía se confirma por validación cruzada.

- **Nombre corto:** SpectraHive. **Nombre largo:** SPHEREx Tracker.
- **Flujo central (no se toca):** buscar por RA/Dec → Blink Época A ↔ B → resta
  |B−A| → reportar anomalía → ADN Cósmico → validación cruzada.
- **Stack congelado:** Vite + React + Tailwind + Aladin Lite (CDN) / FastAPI solo
  (Python) / Supabase PostgreSQL / Astropy + NumPy + SciPy / Vercel + Render /
  **Docker + Docker Compose para desarrollo, pruebas y despliegue del backend**.
  No cambiar el stack a mitad del hackatón.

## 2. Requisitos funcionales

### Búsqueda y navegación

- **RF-01 — Buscar por coordenadas.** El usuario introduce RA y Dec (sexagesimal
  o decimal) y el sistema centra el visor en esa posición. RA válida 0–360°,
  Dec válida −90°…+90°. Coordenadas fuera de rango se rechazan con mensaje claro.
- **RF-02 — FOV.** El usuario elige FOV 1 o 2. Solo esos dos valores. Nada de
  slider continuo ni otros FOV.
- **RF-03 — URL dinámica.** Abrir `/?ra=<RA>&dec=<Dec>&fov=<1|2>` centra el visor
  en esa posición con ese FOV, sin pasos extra. Ejemplo:
  `/?ra=08h55m&dec=-7d14m&fov=2` (WISE 0855). La URL se actualiza al cambiar
  de cuadrante, para poder compartirla.
- **RF-04 — Atajos de prueba.** La UI ofrece los 5 objetos de prueba como atajos
  (ver §5). Un clic centra el visor en ese objeto con FOV 2.
- **RF-05 — Cola fija de cuadrantes.** El sistema recorre una cola fija de
  10 cuadrantes en orden: los 5 de prueba + 5 de práctica. El usuario avanza
  al siguiente cuadrante y puede volver al anterior. No hay cuadrantes aleatorios
  infinitos ni cobertura de todo el cielo.

### Blink y resta

- **RF-06 — Blink entre 2 épocas.** El usuario alterna (scroll / toggle) entre
  Época A y Época B del mismo cuadrante. Solo 2 épocas, siempre el mismo
  cuadrante, misma escala y mismo centro.
- **RF-07 — Falso color único.** Las imágenes se muestran con una sola
  normalización: percentiles 1–99. No hay varias paletas ni ajustes manuales
  por banda en el MVP.
- **RF-08 — Resta |B−A|.** El sistema calcula `Imagen_Diff = |Matriz_B − Matriz_A|`
  y la muestra. Los objetos fijos se cancelan; lo que se movió o cambió de
  brillo queda visible.
- **RF-09 — Umbral y explicación del candidato.** La resta aplica un umbral y el
  sistema explica por qué un punto brillante sí es candidato y otro no
  (valor por encima del umbral, coherencia entre épocas). Sin umbral, la resta
  no se considera terminada.

### Reporte y validación

- **RF-10 — Reportar anomalía.** Sobre un cuadrante, el usuario hace clic en
  una posición y crea un reporte con: `cuadrante_id`, `ra`, `dec`,
  `tipo ∈ {movimiento, brillo, limpio}`. El reporte se guarda en `reportes`.
- **RF-11 — Marcar limpio.** El usuario puede marcar un cuadrante como limpio
  (`tipo = limpio`) sin crear una anomalía. Un cuadrante limpio no genera
  validaciones de confirmación.
- **RF-12 — Validación cruzada.** Un reporte se confirma solo cuando 3
  validaciones con `coincide = true` apuntan al mismo `reporte_id`
  (vista `vw_reportes_confirmados`). Con menos de 3, el reporte sigue pendiente.
- **RF-13 — Votos simulados etiquetados.** En la demo, los 3 votos pueden ser
  simulados, pero siempre con `validaciones.es_simulado = true` y etiquetados
  como simulados en la UI. Nunca presentar un voto simulado como voto real.

### ADN Cósmico

- **RF-14 — ADN Cósmico precalculado.** Para un objeto seleccionado, el sistema
  muestra su ADN Cósmico: un código de barras de color con su firma espectral.
  Los datos vienen precalculados, no se extraen 102 bandas en vivo para
  cualquier clic.
- **RF-15 — ADN es firma visual, no huella química directa.** En la UI y en los
  textos, el ADN Cósmico se presenta como firma visual para comparar, nunca
  como identificación química directa sin calibración.

### Datos

- **RF-16 — Cutouts precalculados + fallback.** El backend sirve cutouts IRSA
  precalculados (DR1 / QR3, FITS multi-extensión). Si IRSA no responde, el
  sistema usa el fallback sintético del demo y lo indica. La demo no se muere
  por falta de red.
- **RF-17 — Entorno Docker reproducible.** Todo el desarrollo, las pruebas y el
  despliegue del backend corren en Docker. El repo lleva `docker-compose.yml`
  con servicios `frontend`, `backend` y `db-local` (Postgres local solo para
  pruebas, ver RN-13). Comandos estándar: `docker compose up --build` para
  levantar todo, `docker compose run backend pytest` para las pruebas del
  backend, `docker compose down` para apagar. Nadie desarrolla contra un
  entorno instalado a mano que los demás no pueden reproducir.

## 3. Reglas de negocio

- **RN-01 — Los 5 objetos son los que el reto pide probar.** Se presentan como
  “los 5 objetos que el reto pide probar” (“Test your tool on...”). Nunca
  “exigidos / obligatorios / mandatorios”.
- **RN-02 — Dos grupos, nunca mezclarlos.** Movimiento: Barnard's Star,
  Epsilon Indi B, WISE 0855. Brillo: RW Aurigae, R Draconis. El campo
  `tipo_prueba ∈ {movimiento, brillo}` lo marca en `cuadrantes` y el campo
  `tipo ∈ {movimiento, brillo, limpio}` lo marca en `reportes`.
- **RN-03 — Brillo no es movimiento.** RW Aurigae (T Tauri) y R Draconis
  (Mira, periodo ~8 meses, mag ~7.6 máx / ~12.4 mín) NO se mueven: en el blink
  cambian de brillo. Un reporte de estos objetos con `tipo = movimiento` es
  incorrecto. En la UI y el tutorial se explican como cambio de brillo.
- **RN-04 — Coordenadas J2000, no se inventa nada.** Todas las coordenadas son
  J2000 y están en §5. No se inventa ninguna coordenada, ni de objetos ni de
  cuadrantes de práctica: los 5 cuadrantes de práctica los elige el equipo
  con coordenadas reales.
- **RN-05 — Propagación del movimiento propio.** Las coordenadas del catálogo
  son J2000. Propagadas a ~2026.9, Barnard se ha movido ~4.7′ y WISE 0855
  ~3.7′. Con FOV 2 los atajos siguen centrando el objeto, pero para cruces
  con catálogos hay que propagar la posición o resolver por nombre
  (SIMBAD / Aladin). No asumir que la posición J2000 es la posición actual.
- **RN-06 — Un cuadrante, un estado.** `cuadrantes.estado ∈ {pendiente,
  confirmado, descartado}`. Un cuadrante pasa a `confirmado` solo cuando uno
  de sus reportes se confirma por RN-12. No hay otros estados.
- **RN-07 — Un reporte, una posición, un tipo.** Cada reporte tiene una sola
  RA, una sola Dec y un solo tipo. No se edita un reporte para cambiar su
  tipo: se crea uno nuevo.
- **RN-08 — La validación es por reporte, no por cuadrante.** Los 3 votos
  cuentan sobre el mismo `reporte_id`, no sobre 3 reportes distintos del
  mismo cuadrante.
- **RN-09 — Sin reproyección general.** Solo se usan pares de épocas ya
  alineados, o desplazamiento entero de píxeles. Si un par no está alineado,
  no se inventa una alineación: se marca y se usa otro par.
- **RN-10 — Sin datos en vivo para cualquier coordenada.** No hay consultas
  TAP genéricas en vivo. Solo cutouts precalculados de los cuadrantes de la
  cola + 1 búsqueda libre con fallback sintético.
- **RN-11 — Lo que no se hace (fuera de alcance).** Sin HiPS propio, sin red
  social, perfiles ni leaderboard, sin más de 2 épocas, sin más de un falso
  color, sin FOV distinto de 1 y 2, sin extracción de 102 bandas en vivo.
  Si una idea nueva no cabe en RF-01…RF-16, no se hace en este MVP.
- **RN-12 — La IA no inventa la idea ni los datos.** La idea ya la definió el
  equipo. La IA ayuda a implementar, redactar y revisar. Código y datos
  asistidos por IA se etiquetan en comentarios/metadatos y en el README
  (`Assisted by <herramienta> (SI) — reviewed by <nombre>`). Imágenes y
  videos generados con SI llevan marca de agua visible. Nada de logos de
  NASA ni identificadores de misión como imagen en contenido generado con SI.
  No se pegan credenciales ni tokens en la IA ni en el repo.
- **RN-13 — Docker es el entorno estándar, Supabase sigue siendo la DB de
  producción.** `db-local` es un Postgres en Docker solo para pruebas locales
  (se le corre `supabase-schema.sql` y se verifica). La base de producción es
  Supabase en la nube, no se dockeriza ni se sustituye por `db-local`.
  Las credenciales van en `.env` (no commiteado) y se pasan al contenedor
  por variables de entorno, nunca hardcodeadas en el `Dockerfile` ni en el
  `docker-compose.yml`. El backend en Render se despliega desde su `Dockerfile`.
  El frontend se despliega en Vercel (build estático); su imagen Docker es
  solo para desarrollo y pruebas locales, no para el despliegue en Vercel.
- **RN-14 — Cambio sustancial: la IA avisa al humano, no lo implementa por su
  cuenta.** Cambio sustancial es cualquier cambio en: el stack, un RF o RN,
  un contrato de API (§6), el modelo de datos (§4), el alcance del MVP, los
  objetos de prueba (§5) o el entorno Docker (RF-17). Ante uno, la IA debe:
  (1) detenerse y NO implementarlo; (2) avisar al humano en el chat qué cambió,
  por qué y qué partes afecta; (3) esperar a que el humano se lo comunique al
  equipo y el equipo lo acuerde; (4) solo entonces actualizar este archivo
  primero y avisar a los 4 roles, y después implementar. Lo que NO es cambio
  sustancial — un bug, un ajuste de estilo o una corrección que no toca
  RF/RN/contratos/datos — se puede hacer y avisar en el momento, sin parar el
  trabajo.

## 4. Modelo de datos (nombres exactos — no renombrar)

Esquema en `../spectrahive-starter-kit/supabase-schema.sql`. Ejecutarlo en el
SQL Editor de Supabase y verificarlo; no se ha probado en vivo.

- **`cuadrantes`**: `id` (uuid, pk), `nombre` (text, unique), `ra` (double,
  grados J2000), `dec` (double, grados J2000), `fov` (numeric, default 2),
  `epoca_a` (text, referencia al cutout A), `epoca_b` (text, referencia al
  cutout B), `estado` (text, `pendiente`/`confirmado`/`descartado`,
  default `pendiente`), `es_objeto_prueba` (boolean), `tipo_prueba`
  (text, `movimiento`/`brillo`), `url_dinamica` (text), `creado_en`.
- **`reportes`**: `id` (uuid, pk), `cuadrante_id` (fk → cuadrantes),
  `ra` (double), `dec` (double), `tipo` (text,
  `movimiento`/`brillo`/`limpio`), `creado_en`.
- **`validaciones`**: `id` (uuid, pk), `reporte_id` (fk → reportes),
  `coincide` (boolean), `es_simulado` (boolean, default false), `creado_en`.
- **`vw_reportes_confirmados`**: vista con `reporte_id` y `votos_coinciden`
  donde `coincide = true`, agrupado, con `count(*) >= 3`.

## 5. Catálogo de objetos de prueba (J2000, FOV 2)

| Objeto | tipo_prueba | RA | Dec | Atajo |
|---|---|---|---|---|
| Barnard's Star | movimiento ~10.39"/año | 17h57m48.50s (269.452075°) | +04°41′36.1″ (+4.693365°) | `/?ra=17h57m&dec=+4d41m&fov=2` |
| WISE 0855-0714 | movimiento ~8.15"/año | 08h55m10.83s (133.795133°) | −07°14′42.5″ (−7.245146°) | `/?ra=08h55m&dec=-7d14m&fov=2` |
| Epsilon Indi B | movimiento ~4.68"/año | 22h04m10.595s (331.044147°) | −56°46′58.24″ (−56.782844°) | `/?ra=22h04m&dec=-56d47m&fov=2` |
| RW Aurigae | brillo (T Tauri) | 05h07m49.456s (76.956067°) | +30°24′04.77″ (30.401326°) | `/?ra=05h07m&dec=+30d24m&fov=2` |
| R Draconis | brillo (Mira) | 16h32m40.23s (248.167625°) | +66°45′17.9″ (+66.754972°) | `/?ra=16h32m&dec=+66d45m&fov=2` |

Fuentes: Barnard + WISE 0855 en `spherex-test-objects.json`; los otros 3 en
`spherex-extra-test-objects.json` (Epsilon Indi B: SIMBAD/Gaia DR3; RW Aurigae:
Wikipedia; R Draconis: AAVSO, secuencia X42732UG).

## 6. Contratos entre roles (formatos exactos)

- `GET /cutout?ra=<decimal>&dec=<decimal>&fov=<1|2>` → imagen del cuadrante
  + JSON `{ra, dec, fov, epoca, fuente: "irsa" | "sintetico"}`.
- `POST /diff` con `{cuadrante_id, epoca_a, epoca_b}` → imagen `|B−A|` +
  JSON `{umbral, candidatos: [{ra, dec, valor, motivo}]}`.
- `POST /report` con `{cuadrante_id, ra, dec, tipo}` → `{reporte_id, estado}`.
  `tipo` debe coincidir con el `tipo_prueba` del cuadrante, salvo `limpio`.
- ADN Cósmico: JSON precalculado por objeto `{objeto, bandas: [...], valores: [...]}`,
  que el rol 03 entrega al rol 01. No se calcula en el front.
- Si un contrato cambia, se actualiza este archivo primero y se avisa a los
  4 roles. Nadie cambia un contrato por su cuenta (ver RN-14: ante un cambio
  sustancial, la IA avisa al humano y se detiene hasta que el equipo lo acuerde).

## 7. Orden de ejecución y definición de “listo”

1. **Bloque A (en paralelo):** 01 Blink + 02 `/cutout` y `/diff` + 03 esquema
   Supabase. Checkpoint: **blink real con Barnard funcionando**.
2. **Bloque B (después de A):** reporte + validación (03), ADN precalculado (03),
   integración completa con los 5 objetos.
3. **Bloque C (en paralelo, sin bloquear A/B):** entrega en inglés + demo
   (rol 04). La demo se graba al final, con el proyecto funcionando.
4. **“Listo” por rol** está en su archivo 01–04. “Listo” del proyecto: blink
   real con Barnard, resta con umbral, reporte guardado y confirmado con
   3 votos (simulados y etiquetados), ADN visible, links públicos probados.

## 8. Nota breve de entrega (solo para el rol 04)

La entrega es la página del proyecto en inglés (resumen, descripción, demo
≤30 s o ≤7 diapositivas, links públicos sin login, declaración de SI, datos
de NASA y referencias). Cierre domingo 15 nov 23:59 hora local; dar
“Submit for Judging” antes. Los detalles están en `04-entrega-demo-ingles.md`,
no en este archivo.
