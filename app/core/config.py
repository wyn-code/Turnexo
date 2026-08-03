import decouple


SECRET_KEY = decouple.config("SECRET_KEY", default="change-this-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(decouple.config("ACCESS_TOKEN_EXPIRE_MINUTES", default=60))
TWO_FACTOR_TOKEN_EXPIRE_HOURS = int(decouple.config("TWO_FACTOR_TOKEN_EXPIRE_HOURS", default=9))
RESEND_API_KEY = decouple.config("RESEND_API_KEY")
FRONTEND_URL = decouple.config("FRONTEND_URL", default="https://www.turnogo.app")
MAPBOX_ACCESS_TOKEN = decouple.config("MAPBOX_ACCESS_TOKEN")
BACKEND_URL = decouple.config("BACKEND_URL")
MERCADOPAGO_ACCESS_TOKEN = decouple.config("MERCADOPAGO_ACCESS_TOKEN")
GOOGLE_CLIENT_ID = decouple.config("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = decouple.config("GOOGLE_CLIENT_SECRET")
