-- Agrandar otp_code para almacenar el hash HMAC-SHA256 (64 chars) en lugar de texto plano.
alter table public.usuarios
  alter column otp_code type varchar(64);