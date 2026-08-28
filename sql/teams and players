-- ============================================================
-- DEMO — Liga ficticia
-- Datos sintéticos generados para demostración. Ninguna persona real.
-- ============================================================

create table equipos (
    id      smallint primary key,
    nombre  text not null unique,
    es_propio boolean not null default false
);

insert into equipos (id, nombre, es_propio) values
    (1,  'Jaguares', true),
    (2,  'Panteras', false),
    (3,  'Koalas',   false),
    (4,  'Gaviotas', false),
    (5,  'Ardillas', false),
    (6,  'Búfalos',  false),
    (7,  'Águilas',  false),
    (8,  'Gacelas',  false),
    (9,  'Osos',     false),
    (10, 'Lobos',    false);


-- ============================================================
-- Plantilla del equipo propio
-- ============================================================

create table jugadoras (
    id            smallint primary key,
    equipo_id     smallint not null references equipos(id),
    dorsal        smallint not null,
    nombre        text not null,
    nombre_corto  text not null,
    posicion      text not null check (posicion in ('Por','Def','MC','Del')),
    activa        boolean not null default true,
    unique (equipo_id, dorsal)
);

insert into jugadoras (id, equipo_id, dorsal, nombre, nombre_corto, posicion) values
    -- Porteras
    (1,  1,  1, 'Aike Moreno',      'Aike',    'Por'),
    (2,  1, 13, 'Blair Sanchís',    'Blair',   'Por'),
    (3,  1, 25, 'Quinn Ferrer',     'Quinn',   'Por'),
    -- Defensas
    (4,  1,  2, 'Alex Ribera',      'Alex',    'Def'),
    (5,  1,  3, 'Cruz Iglesias',    'Cruz',    'Def'),
    (6,  1,  4, 'Darcy Peris',      'Darcy',   'Def'),
    (7,  1,  5, 'Gael Montalt',     'Gael',    'Def'),
    (8,  1, 12, 'Kin Bautista',     'Kin',     'Def'),
    (9,  1, 15, 'Noa Server',       'Noa',     'Def'),
    (10, 1, 21, 'Ariel Tormo',      'Ariel',   'Def'),
    -- Mediocampo
    (11, 1,  6, 'Aimar Bosch',      'Aimar',   'MC'),
    (12, 1,  8, 'Dani Colomer',     'Dani',    'MC'),
    (13, 1, 14, 'Francis Alcaraz',  'Francis', 'MC'),
    (14, 1, 16, 'Jaz Fuertes',      'Jaz',     'MC'),
    (15, 1, 18, 'Mica Llopis',      'Mica',    'MC'),
    (16, 1, 20, 'Kai Benavent',     'Kai',     'MC'),
    (17, 1, 23, 'Taylor Ochoa',     'Taylor',  'MC'),
    -- Delanteras
    (18, 1,  7, 'Hodei Ramos',      'Hodei',   'Del'),
    (19, 1,  9, 'Indigo Marzal',    'Indigo',  'Del'),
    (20, 1, 10, 'Leslie Andrés',    'Leslie',  'Del'),
    (21, 1, 11, 'Neftalí Cardona',  'Neftalí', 'Del'),
    (22, 1, 17, 'Fénix Aparicio',   'Fénix',   'Del'),
    (23, 1, 19, 'Rosario Gimeno',   'Rosario', 'Del'),
    (24, 1, 22, 'Dana Chulvi',      'Dana',    'Del');
