-- Assisted by Antigravity (SI) — reviewed by Jeshua
-- SpectraHive — Esquema PostgreSQL / Supabase (fuente de verdad / respaldo + db-local)

create extension if not exists pgcrypto;

create table if not exists cuadrantes (
    id uuid primary key default gen_random_uuid(),
    nombre text unique not null,
    ra float8 not null,
    dec float8 not null,
    fov numeric not null default 2,
    epoca_a text,
    epoca_b text,
    estado text not null default 'pendiente'
        check (estado in ('pendiente', 'confirmado', 'descartado')),
    es_objeto_prueba boolean not null default false,
    tipo_prueba text
        check (tipo_prueba in ('movimiento', 'brillo')),
    url_dinamica text,
    creado_en timestamptz not null default now()
);

create table if not exists reportes (
    id uuid primary key default gen_random_uuid(),
    cuadrante_id uuid references cuadrantes(id) on delete cascade,
    ra float8 not null,
    dec float8 not null,
    tipo text not null
        check (tipo in ('movimiento', 'brillo', 'limpio')),
    creado_en timestamptz not null default now()
);

create index if not exists idx_reportes_cuadrante on reportes(cuadrante_id);

create table if not exists validaciones (
    id uuid primary key default gen_random_uuid(),
    reporte_id uuid not null references reportes(id) on delete cascade,
    coincide boolean not null,
    es_simulado boolean not null default false,
    creado_en timestamptz not null default now()
);

create index if not exists idx_validaciones_reporte on validaciones(reporte_id);

create or replace view vw_reportes_confirmados as
select
    reporte_id,
    count(*) as votos_coinciden
from validaciones
where coincide = true
group by reporte_id
having count(*) >= 3;

-- Semillas de los 5 objetos de prueba (J2000, FOV 2)
insert into cuadrantes (
    nombre,
    ra,
    dec,
    fov,
    epoca_a,
    epoca_b,
    estado,
    es_objeto_prueba,
    tipo_prueba,
    url_dinamica
)
values
    (
        'Barnard''s Star',
        269.452075,
        4.693365,
        2,
        'DR1',
        'QR3',
        'pendiente',
        true,
        'movimiento',
        '/?ra=17h57m&dec=+4d41m&fov=2'
    ),
    (
        'WISE 0855-0714',
        133.795133,
        -7.245146,
        2,
        'DR1',
        'QR3',
        'pendiente',
        true,
        'movimiento',
        '/?ra=08h55m&dec=-7d14m&fov=2'
    ),
    (
        'Epsilon Indi B',
        331.044147,
        -56.782844,
        2,
        'DR1',
        'QR3',
        'pendiente',
        true,
        'movimiento',
        '/?ra=22h04m&dec=-56d47m&fov=2'
    ),
    (
        'RW Aurigae',
        76.956067,
        30.401326,
        2,
        'DR1',
        'QR3',
        'pendiente',
        true,
        'brillo',
        '/?ra=05h07m&dec=+30d24m&fov=2'
    ),
    (
        'R Draconis',
        248.167625,
        66.754972,
        2,
        'DR1',
        'QR3',
        'pendiente',
        true,
        'brillo',
        '/?ra=16h32m&dec=+66d45m&fov=2'
    )
on conflict (nombre) do nothing;
