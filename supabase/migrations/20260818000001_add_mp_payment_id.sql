-- Agregar mp_payment_id (único) a suscripciones para idempotencia del webhook MP.
alter table public.suscripciones
  add column if not exists mp_payment_id varchar(150);

create unique index if not exists uq_suscripciones_mp_payment_id
  on public.suscripciones (mp_payment_id)
  where mp_payment_id is not null;