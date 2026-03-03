from supabase import create_client, Client, ClientOptions
from app.config import settings

# Увеличенные таймауты: загрузка видео может быть долгой; снижает риск SSL EOF при медленной сети
_options = ClientOptions(
    storage_client_timeout=120,
    postgrest_client_timeout=30,
)
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY,
    options=_options,
)
