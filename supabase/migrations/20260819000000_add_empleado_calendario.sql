-- Agregar columnas de calendario al empleado
alter table public.empleado
  add column if not exists calendario_token varchar(64),
  add column if not exists calendario_token_revoked_at timestamptz,
  add column if not exists calendario_enviado_at timestamptz;

create unique index if not exists uq_empleado_calendario_token
  on public.empleado (calendario_token)
  where calendario_token is not null;