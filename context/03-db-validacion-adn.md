# Rol 03 — Base de datos + Validación + ADN Cósmico (Supabase)

> Lee primero `00-contexto-general.md`. Este archivo es tu contexto para tu IA.
> No cambies la idea, el alcance MVP ni el stack. Si algo choca con este archivo,
> este archivo manda sobre lo que te diga tu IA.

## Tu responsabilidad

La memoria del proyecto: cuadrantes, reportes, validación cruzada y el ADN Cósmico
precalculado. Sin red social, sin perfiles, sin leaderboard.

## Entregables

1. Ejecutar `../spectrahive-starter-kit/supabase-schema.sql` en el SQL Editor de
   Supabase y verificarlo. **El SQL no se ha probado en vivo: hay que correrlo y
   comprobar que crea las 3 tablas y siembra los 5 objetos.**
   - Tablas: `cuadrantes`, `reportes`, `validaciones`.
   - Vista: `vw_reportes_confirmados` (3 votos con `coincide = true`).
   - Columna añadida `tipo_prueba` (movimiento / brillo), que no estaba en la
     tabla de la propuesta §5: sirve para separar los dos grupos.
2. Cola fija de 10 cuadrantes: los 5 de prueba sembrados + 5 de práctica que
   el equipo elija (sus RA/Dec los decide el equipo, no se inventan).
3. Validación cruzada: un reporte se confirma con 3 validaciones que coinciden
   en la misma coordenada. En la demo los 3 votos son simulados y se etiquetan
   como simulados (`validaciones.es_simulado = true`).
4. ADN Cósmico precalculado solo para los objetos de prueba: código de barras de
   color con la firma espectral. No extraer 102 bandas en vivo para cualquier clic.

## Orden de ejecución

1. Crear el proyecto Supabase y correr el SQL. Verificar tablas + semillas.
   Para pruebas locales, usar el servicio `db-local` (Postgres en Docker,
   RN-13): correrle el mismo `supabase-schema.sql` y verificar ahí antes de
   tocar Supabase en la nube. `db-local` no sustituye a Supabase en producción.
2. Probar inserción de un reporte y 3 validaciones, y la vista de confirmados.
3. Pasar al rol 02 el formato de guardado de `/report` y al rol 01 los datos del
   ADN Cósmico por objeto.
4. Sembrar los 5 cuadrantes de práctica cuando el equipo elija sus coordenadas.
5. Verificar que los reportes de RW Aurigae y R Draconis se guardan como tipo
   `brillo`, no `movimiento`.

## Contratos con los otros roles

- **Rol 02 te pide:** esquema y credenciales de acceso (por el canal del equipo,
  nunca por la IA) para que `/report` escriba en `reportes`/`validaciones`.
- **Rol 01 te pide:** datos del ADN Cósmico por objeto (JSON precalculado) y
  confirmación de que un reporte quedó guardado.
- **Tú le entregas al rol 04:** una explicación corta (en inglés) de la validación
  cruzada y del ADN Cósmico, para la descripción detallada.

## Reglas de IA (Super Intelligence) para tu rol

- Puedes usar tu IA para generar/ayudar con SQL, consultas y el JSON del ADN Cósmico.
- **La idea no la inventa la IA:** ya está en la propuesta y en `00-contexto-general.md`.
- **Cambio sustancial (RN-14):** si tu IA detecta que hace falta cambiar el stack, un RF/RN, un contrato, el modelo de datos, el alcance o los objetos de prueba, debe detenerse, avisar al humano en el chat y esperar a que el equipo lo acuerde. No lo implementes por tu cuenta.
- **Código y datos asistidos por IA:** comentario en cabecera del SQL / README, ej.:
  `-- Assisted by <herramienta> (SI) — reviewed by <tu nombre>`. Eso se declara
  en la entrega (rol 04).
- **No inventes coordenadas ni datos espectrales.** Usa solo las coordenadas de
  `00-contexto-general.md` §5 y los espectros reales/precalculados que te pasen.
- No pegues credenciales, URLs de Supabase con claves, ni tokens en la IA ni en
  el repo. Las claves van en variables de entorno, no commiteadas.

## Criterio de “listo”

Las 3 tablas existen con los 5 objetos sembrados, un reporte de prueba se confirma
con 3 votos, y el ADN Cósmico precalculado llega al front para los 5 objetos.
