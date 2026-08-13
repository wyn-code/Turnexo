-- Add otp_attempts (intentos de OTP) a usuarios
-- Límite de reintentos de /verify-2fa: 5; se resetea en login/resend.

ALTER TABLE public.usuarios
ADD COLUMN IF NOT EXISTS otp_attempts integer NOT NULL DEFAULT 0;