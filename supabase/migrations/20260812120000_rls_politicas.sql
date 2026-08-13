-- Políticas RLS para Turnogo
--
-- RLS ya está habilitado en todas las tablas del esquema public, pero no existía
-- ninguna política, por lo que anon/authenticated no podían leer ni escribir nada
-- vía PostgREST y la app (conexión directa como dueño/service_role) quedaba fuera
-- del filtrado de RLS.
--
-- Objetivo:
--   1. Permitir lectura pública (anon + authenticated) solo del catálogo público:
--      negocios, servicios, categorías, imágenes, horarios, estados, geografía y planes.
--   2. Mantener DENEGADO el acceso vía PostgREST a los datos sensibles
--      (usuarios, turnos, clientes, empleados, suscripciones, features).
--
-- La app NO usa PostgREST: se conecta por DATABASE_URL con un rol que tiene
-- BYPASSRLS (postgres/service_role), por lo que estas políticas no modifican su
-- comportamiento.

-- ---------------------------------------------------------------------------
-- Catálogo público: lectura para anon y authenticated
-- ---------------------------------------------------------------------------

create policy "public_read_negocio"
on public.negocio
for select
to anon, authenticated
using (true);

create policy "public_read_servicio"
on public.servicio
for select
to anon, authenticated
using (true);

create policy "public_read_estado_turno"
on public.estado_turno
for select
to anon, authenticated
using (true);

create policy "public_read_categorias"
on public.categorias
for select
to anon, authenticated
using (true);

create policy "public_read_localidades"
on public.localidades
for select
to anon, authenticated
using (true);

create policy "public_read_provincia"
on public.provincia
for select
to anon, authenticated
using (true);

create policy "public_read_negocio_imagen"
on public.negocio_imagen
for select
to anon, authenticated
using (true);

create policy "public_read_horarios_negocio"
on public.horarios_negocio
for select
to anon, authenticated
using (true);

create policy "public_read_planes"
on public.planes
for select
to anon, authenticated
using (true);

-- ---------------------------------------------------------------------------
-- Datos sensibles: sin políticas -> anon/authenticated DENEGADOS vía PostgREST.
-- Las tablas usuario, turno, cliente, empleado, suscripciones y plan_features
-- quedan accesibles únicamente por el rol de la app (bypass RLS).
-- ---------------------------------------------------------------------------
