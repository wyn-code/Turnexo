-- Negocio: vincular provincia/localidad en cascada.
-- 1) Backfill: mapear el string "ciudad" existente a una localidad
--    (solo cuando el nombre es único, sino queda id_localidad NULL).
-- 2) Garantía a nivel de DB: la localidad debe pertenecer a la provincia
--    del negocio (FK compuesta). Se agrega solo si los datos actuales son consistentes.

-- ───────────────────────── 1) BACKFILL ciudad → localidad ─────────────────────────
do $$
declare
    prov_tbl text;
    neg_tbl text;
begin
    select table_name into prov_tbl
    from information_schema.tables
    where table_schema = 'public' and table_name in ('provincia', 'provincias')
    order by (table_name = 'provincia') desc
    limit 1;

    select table_name into neg_tbl
    from information_schema.tables
    where table_schema = 'public' and table_name in ('negocio', 'negocios')
    order by (table_name = 'negocio') desc
    limit 1;

    if prov_tbl is not null and neg_tbl is not null then
        execute format($b$
            update public.%I n
            set id_localidad = l.id_localidad,
                id_provincia  = l.id_provincia,
                ciudad        = l.nombre
            from public.localidades l
            where n.id_localidad is null
              and n.ciudad is not null
              and trim(n.ciudad) <> ''
              and lower(trim(n.ciudad)) = lower(trim(l.nombre))
              and not exists (
                  select 1
                  from public.localidades l2
                  where lower(trim(l2.nombre)) = lower(trim(n.ciudad))
                  group by lower(trim(l2.nombre))
                  having count(*) > 1
              )
        $b$, neg_tbl);
    end if;
end $$;

-- ───────────────── 2) FK compuesta (localidad ∈ provincia) ─────────────────
-- Índice único requerido por la FK compuesta.
create unique index if not exists "localidades_id_localidad_id_provincia_key"
    on public.localidades (id_localidad, id_provincia);

do $$
declare
    neg_tbl text;
    violations int;
begin
    select table_name into neg_tbl
    from information_schema.tables
    where table_schema = 'public' and table_name in ('negocio', 'negocios')
    order by (table_name = 'negocio') desc
    limit 1;

    if neg_tbl is not null then
        execute format($b$
            select count(*)
            from public.%I n
            join public.localidades l on l.id_localidad = n.id_localidad
            where n.id_localidad is not null
              and n.id_provincia is not null
              and l.id_provincia <> n.id_provincia
        $b$, neg_tbl) into violations;

        if violations = 0 then
            execute format($b$
                alter table public.%I
                add constraint "fk_negocio_localidad_provincia"
                foreign key (id_localidad, id_provincia)
                references public.localidades (id_localidad, id_provincia)
            $b$, neg_tbl);
        end if;
    end if;
end $$;
