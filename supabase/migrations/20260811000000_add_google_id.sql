-- Add google_id to usuarios for account linking

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_google_id ON usuarios(google_id);
