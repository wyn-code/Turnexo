-- Add Google OAuth support to usuarios table

-- Make password nullable (Google users won't have one)
ALTER TABLE usuarios ALTER COLUMN contrasena_us DROP NOT NULL;

-- Add auth provider column
ALTER TABLE usuarios ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'local';
