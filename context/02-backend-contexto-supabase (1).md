# SpectraHive — Contexto de Supabase para el backend (rol 02)

> Fuente: `SpectraHive_Base_de_Datos_Supabase.pdf` (resumen del equipo, capturas
> del panel de Supabase del 14 nov 2026, 13:39–13:40 CST) + verificación de
> coherencia contra `00-contexto-general.md`, `02-backend-arquitectura.md` y
> `supabase-schema.sql` (2026-11-14 ~13:55).
> **Este documento NO contiene secretos.** Las credenciales van en `.env`
> (nunca commiteado) y en variables de entorno de Render. Si ves una clave
> en algún documento, no la copies al repo: avisa y se retira.

## 1. El proyecto (hechos, sin secretos)

- **Proyecto / organización:** `spectrahive-db` / `spectrahive-database`
- **Plan:** Free. Rama `main` marcada como Production. **Sin respaldos**
  ("No backups") y **sin migraciones registradas**.
- **Región:** West US (Oregon), `us-west-2`. Instancia Nano.
- **Versiones:** Postgres **17.11**, PostgREST 14.18, Auth 2.197.0.
- **Estado:** Healthy. CPU 2%, disco 13%, RAM 53%, 5 de 60 conexiones.
  Últimos 60 min: 52 solicitudes, 94.2% exitosas (~3 fallaron; revisar Logs).
- **Esquema:** `public`, 3 tablas: `cuadrantes`, `reportes`, `validaciones`.
- **GitHub (Supabase):** repo `Ilyavosky/spectrahive-database` conectado,
  despliegue activado desde `main`. **No confundir con el repo del backend
  (`JILZXY/SpectraHive-backend`)**: son repos distintos.
- **Fuente de verdad del esquema:** `supabase-schema.sql` (starter kit).
  La integración de GitHub de Supabase busca una carpeta `supabase/` y el
  repo solo tiene el `.sql` en la raíz: **hacer push NO cambia la base**.
  Los cambios de esquema se aplican a mano en el SQL Editor.

## 2. Tablas (nombres exactos — no renombrar)

### `cuadrantes` — la cola de cuadrantes

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid, PK | `default gen_random_uuid()` |
| `nombre` | text, unique, not null | |
| `ra`, `dec` | float8, not null | Grados decimales, **J2000** |
| `fov` | numeric, not null, default 2 | MVP: solo 1 y 2 |
| `epoca_a`, `epoca_b` | text | Referencia al cutout A / B |
| `estado` | text, not null, default `'pendiente'` | `CHECK (estado IN ('pendiente','confirmado','descartado'))` |
| `es_objeto_prueba` | boolean, not null, default false | |
| `tipo_prueba` | text | `CHECK (tipo_prueba IN ('movimiento','brillo'))` |
| `url_dinamica` | text | Atajo `/?ra=...&dec=...&fov=2` |
| `creado_en` | timestamptz, not null | `default now()` |

### `reportes` — una anomalía reportada

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid, PK | `default gen_random_uuid()` |
| `cuadrante_id` | uuid, FK → `cuadrantes(id)` | |
| `ra`, `dec` | float8, not null | Una sola posición por reporte (RN-07) |
| `tipo` | text, not null | `CHECK (tipo IN ('movimiento','brillo','limpio'))` — un solo tipo por reporte |
| `creado_en` | timestamptz, not null | `default now()` |

Índice: `idx_reportes_cuadrante (cuadrante_id)`.

### `validaciones` — un voto sobre un reporte

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid, PK | `default gen_random_uuid()` |
| `reporte_id` | uuid, not null, FK → `reportes(id)` | |
| `coincide` | boolean, not null | |
| `es_simulado` | boolean, not null, default false | Votos simulados de la demo: siempre `true` y etiquetados en UI |
| `creado_en` | timestamptz, not null | `default now()` |

Índice: `idx_validaciones_reporte (reporte_id)`.

### Vista `vw_reportes_confirmados` — la regla de validación cruzada (RF-12)

```sql
select reporte_id, count(*) as votos_coinciden
from validaciones
where coincide = true
group by reporte_id
having count(*) >= 3;
```

**Es la fuente de verdad para lectura:** un reporte está confirmado si
aparece en esta vista. El backend no reimplementa el conteo: lo consulta.

## 3. Semillas: los 5 objetos de prueba (ya cargados según el script)

| Objeto | `tipo_prueba` | RA / Dec (J2000) | Atajo |
|---|---|---|---|
| Barnard's Star | movimiento | 269.452075, +4.693365 | `/?ra=17h57m&dec=+4d41m&fov=2` |
| WISE 0855-0714 | movimiento | 133.795133, −7.245146 | `/?ra=08h55m&dec=-7d14m&fov=2` |
| Epsilon Indi B | movimiento | 331.044147, −56.782844 | `/?ra=22h04m&dec=-56d47m&fov=2` |
| RW Aurigae | brillo | 76.956067, +30.401326 | `/?ra=05h07m&dec=+30d24m&fov=2` |
| R Draconis | brillo | 248.167625, +66.754972 | `/?ra=16h32m&dec=+66d45m&fov=2` |

Los otros 5 cuadrantes de la cola fija de 10 son de práctica: el equipo elige
5 coordenadas reales (RN-04, no inventar) y se agregan con `INSERT`.

## 4. Cómo se conecta el backend (decisión recomendada)

El PDF dejaba pendiente el método (librería cliente, cadena directa u ORM).
**Decisión recomendada para el rol 02: conexión directa a Postgres con
`psycopg` (v3) y pool**, por tres motivos: (1) los repositorios necesitan
transacciones (voto + cambio de `estado` atómicos, §5); (2) se lee la vista
con SQL normal; (3) el mismo código corre contra `db-local` y contra
Supabase cambiando solo `DATABASE_URL` (RF-17).

### 4.1 Glosario Supabase: qué es cada cosa (y qué usa el backend)

Supabase no es solo una base de datos: es una plataforma con varias piezas
encima del mismo Postgres. El backend **solo usa el Postgres**; el resto
existe pero no se usa en el MVP.

- **PostgreSQL:** la base de datos en sí (tablas, vistas, CHECKs). Es lo
  único que el backend toca.
- **PostgREST:** un servicio que genera automáticamente una API REST a partir
  de las tablas (`GET /rest/v1/cuadrantes`, etc.). Es lo que usan por dentro
  las librerías cliente de Supabase (JS/Python) cuando hacen
  `supabase.from("cuadrantes").select()`. **El backend NO lo usa:** al
  conectarse directo con `psycopg`, se salta PostgREST y habla SQL directo
  con Postgres. Por eso el `DATABASE_URL` es una cadena `postgresql://...`
  y no una URL de API.
- **Auth (GoTrue):** servicio de usuarios/login (registro, JWT, proveedores).
  Existe en el proyecto (versión 2.197.0) pero **no se usa en el MVP**
  (RN-11: sin usuarios/perfiles/leaderboard).
- **Storage:** almacenamiento de archivos. No se usa en el MVP.
- **Realtime:** suscripciones en vivo a cambios de tablas. No se usa.
- **Edge Functions:** funciones serverless. No se usan.
- **Supavisor (pooler):** un intermediario que mantiene un pool de conexiones
  a Postgres para que muchos clientes (como Render) no agoten las 60
  conexiones del plan Free. Su cadena de conexión usa el puerto **6543**
  (la directa usa 5432).
- **SQL Editor / Dashboard:** el panel web de Supabase, donde se corrió el
  esquema y donde se copian las credenciales. No es parte del código.

### 4.2 Dos modos, un solo código (local vs producción)

> **REGLA PARA LA IA DE DESARROLLO:** hay UNA sola forma de conectar y UNA
> sola variable, `DATABASE_URL`. El código NUNCA lleva hardcodeado el host,
> el puerto, el usuario ni la contraseña, y NUNCA decide por su cuenta a qué
> base conectarse: lee `DATABASE_URL` del entorno y falla rápido si no
> existe. Lo único que cambia entre modos es el VALOR de esa variable,
> que pone Jeshua en el `.env` (local) o en Render (producción).

| Modo | Base de datos | Valor de `DATABASE_URL` | Cuándo se usa |
|---|---|---|---|
| **Local / pruebas** | `db-local`: Postgres 17 en Docker (servicio `db-local` del `docker-compose.yml`) | Apunta a `db-local:5432` (la pone el compose; ver `.env.example`) | Desarrollo y `docker compose run backend pytest`. Solo para pruebas: los datos que se escriben aquí se tiran |
| **Producción** | Supabase real (`spectrahive-db`, Oregon) | Cadena del pooler Supavisor (puerto 6543) del panel de Supabase | Cuando la API se instancia en Render. Es la base de verdad: lo que se escriba aquí es lo que ven los jueces |

- El mismo `supabase-schema.sql` se corre en ambas (RF-17), así que el
  código no nota la diferencia: mismas tablas, misma vista, mismos nombres.
- **`.env.example`** lleva el valor de ejemplo apuntando a `db-local`
  (con usuario/contraseña de pruebas, sin secretos reales). El valor de
  producción **solo existe en el panel de Render**, nunca en el repo ni en
  ningún `.env` commiteado.
- Si al arrancar `DATABASE_URL` no está definida, la API debe fallar
  explícitamente ("falta DATABASE_URL") en vez de inventar una conexión
  por defecto: un default silencioso es como se terminan mezclando datos
  de pruebas con datos reales.
- **Variables de entorno que el backend necesita (nombres, sin valores):**
  `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
  Se copian del panel de Supabase (Settings → API / Database) al `.env`
  local y a las variables de entorno de Render. **El PDF no trae ningún
  valor de estas variables: no hay nada que copiar de él al `.env`.**
  (Jeshua se encarga de ponerlas en el `.env`.)
- **La clave `anon` NO la usa el backend y NO debe llegar al frontend.**
  Como RLS está desactivado (ver §6), la clave anon equivale a acceso total
  a las tablas.
- **Si usas el pooler en modo transacción:** desactiva los prepared
  statements del lado del servidor (`psycopg`: `prepare_threshold=0`) o usa
  la conexión directa (puerto 5432). Sin esto, las consultas preparadas
  fallan contra el pooler.
- **Alternativa válida:** cliente `supabase-py` con la clave de servicio.
  Si el equipo la prefiere, el cambio es solo del adaptador
  (`infrastructure/supabase/`), no del dominio ni de los contratos. En ese
  caso las variables serían `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`
  y `DATABASE_URL` dejaría de usarse para los repositorios.

## 5. Qué toca cada caso de uso (mapeo repositorio ↔ endpoint)

| Caso de uso (arquitectura §4) | Tablas | Notas |
|---|---|---|
| `GetCutout` | `cuadrantes` (lectura) | Lee `epoca_a`/`epoca_b` y `url_dinamica` del cuadrante; el FITS no vive en la BD |
| `ComputeDiff` | `cuadrantes` (lectura) | No escribe en BD; solo lee referencias de épocas |
| `CreateReport` | `reportes` (insert) | Valida RN-02/RN-03 en dominio **antes** de insertar; el `CHECK` de `tipo` es la segunda línea de defensa |
| `ValidateReport` | `validaciones` (insert) + `cuadrantes` (update `estado`) | **El backend es dueño de RN-06:** al insertar un voto, en la misma transacción consulta `vw_reportes_confirmados`; si el reporte ya está confirmado, actualiza `cuadrantes.estado = 'confirmado'`. No existe trigger que lo haga |
| `GetCosmicDNA` | — | El ADN precalculado vive en `data/spectra/` (JSON), no en la BD |
| `ListQuadrants` | `cuadrantes` (lectura) | Cola fija de 10, ordenada; los 5 de práctica llegan después |

## 6. Seguridad: RLS desactivado (qué significa para el backend)

- El script **no activa RLS** (`rowsecurity = false` en las 3 tablas, según
  las comprobaciones del PDF §6). Verificarlo con la consulta de §8.
- **Consecuencia:** quien tenga una clave válida puede leer/escribir todo.
  Por eso el modelo es: **el frontend nunca habla con Supabase** (no tiene
  ninguna clave) y **solo el backend conoce las credenciales** (service role
  / conexión directa). Esto es coherente con RN-12 y RN-13.
- **No activar RLS a mitad del hackatón sin acuerdo del equipo** (RN-14):
  con RLS activo, la conexión directa del backend seguiría funcionando, pero
  cualquier acceso con clave anon se rompería. Si el equipo lo decide, se
  hace con políticas explícitas y se prueba antes de la demo.

## 7. Verificación de coherencia (PDF vs documentación existente)

Verificado 2026-11-14 ~13:55 contra `00-contexto-general.md` (§4 modelo de
datos, §5 catálogo, RF-12, RF-17, RN-04, RN-06, RN-12, RN-13),
`supabase-schema.sql`, `02-backend-arquitectura.md` (§5, §11 CoVe V5/V9) y
la propuesta corregida (§5–§6).

| # | Comprobación | Veredicto |
|---|---|---|
| C1 | Tablas, columnas, tipos, defaults y `CHECK`s (`estado`, `tipo_prueba`, `tipo`) idénticos a 00 §4 y a `supabase-schema.sql` | ✅ Coherente |
| C2 | Vista `vw_reportes_confirmados` (≥ 3 votos `coincide = true`) = RF-12 | ✅ Coherente |
| C3 | Semillas: 5 objetos, coordenadas J2000 y atajos = 00 §5 | ✅ Coherente |
| C4 | RLS desactivado, solo el backend conoce credenciales = RN-12/RN-13 y arquitectura §5 | ✅ Coherente (con la advertencia de §6) |
| C5 | Mismo `supabase-schema.sql` en `db-local` y en Supabase = RF-17 | ✅ Coherente |
| C6 | PostgREST/Auth disponibles pero sin uso en el MVP = RN-11 (fuera de alcance) | ✅ Coherente |
| C7 | RN-06 (cuadrante → `confirmado` solo cuando uno de sus reportes se confirma): el script no trae trigger | ⚠ **El backend lo implementa** (§5). Decisión tomada aquí, no en la BD |
| C8 | `tipo_prueba` no estaba en la tabla de la propuesta §5; el script lo añade | ✅ Coherente (ya documentado en el kit; es la columna que separa movimiento/brillo) |
| C9 | Postgres 17.11 en Supabase; `db-local` sin versión fijada en los docs | ⚠ **Fijar `postgres:17` en el `docker-compose.yml`** para paridad (el esquema es agnóstico a la versión, pero 17 = lo que corre en producción) |
| C10 | Región Oregon (us-west-2); región de Render no fijada en los docs | ⚠ **Desplegar el backend en Render en Oregon** para no sumar latencia |
| C11 | Repo de Supabase (`Ilyavosky/spectrahive-database`) ≠ repo del backend (`JILZXY/SpectraHive-backend`); la integración espera carpeta `supabase/` y el `.sql` está en la raíz | ⚠ No es un error, pero **hacer push no cambia la base**: el esquema se aplica en el SQL Editor y el `.sql` es el respaldo |
| C12 | "Supabase directo para CRUD" (idea inicial) vs "el frontend nunca habla con la base" (PDF) | ✅ Resuelto: **todo pasa por FastAPI** (`POST /report` es el contrato). "Directo" significa que los repositorios del backend hablan directo a Postgres, no que el frontend lo haga (ver arquitectura §11, V9) |
| C13 | Plan Free sin respaldos ni migraciones | ⚠ El `.sql` en el repo es el único respaldo. No borrarlo ni editarlo sin acuerdo |
| C14 | 52 solicitudes, 94.2% exitosas (~3 fallaron, sin identificar) | ✅ Aclarado por Jeshua 2026-11-14 ~14:05: fueron pruebas irrelevantes, sin problema |

**No verificable desde las capturas** (lo dice el propio PDF): que la vista
exista en Supabase, que las 5 filas semilla estén cargadas y el estado real
de RLS. Se comprueba con §8.

## 8. Comprobaciones rápidas (SQL Editor de Supabase, antes de programar)

```sql
-- Debe devolver 5 filas:
select nombre, tipo_prueba, estado from cuadrantes order by nombre;

-- Debe devolver 1 fila con la vista:
select viewname from pg_views where viewname = 'vw_reportes_confirmados';

-- Debe devolver rowsecurity = false en las tres tablas (RLS desactivado):
select tablename, rowsecurity from pg_tables where schemaname = 'public';

-- Prueba de validación cruzada (dentro de transacción, no deja datos):
begin;
with c as (select id from cuadrantes where nombre = 'Barnard''s Star'),
r as (insert into reportes (cuadrante_id, ra, dec, tipo)
      select id, 269.452075, 4.693365, 'movimiento' from c returning id)
insert into validaciones (reporte_id, coincide, es_simulado)
select r.id, true, true from r, generate_series(1, 3);
select * from vw_reportes_confirmados;
rollback;
```

## 9. Riesgos y pendientes (para el backend)

1. **Pausa por inactividad (plan Free):** un proyecto pausado hace fallar la
   demo. Hacer una consulta antes de grabar la demo y antes del Submit.
2. **Cuadrantes de práctica:** faltan 5 de 10. El equipo elige las
   coordenadas; el backend no inventa ninguna (RN-04).
3. **RN-06 sin trigger:** si `ValidateReport` no actualiza `estado`, ningún
   cuadrante se marcará `confirmado` aunque sus reportes sí lo estén.
   Probarlo con la consulta de §8 + un voto real.
4. **Las ~3 solicitudes fallidas:** Jeshua confirmó 2026-11-14 ~14:05 que
   fueron pruebas irrelevantes, sin problema. No requieren acción.
5. **Cierre:** domingo 15 nov, 23:59. Congelar la base y probar los links en
   navegador privado antes de esa hora.
