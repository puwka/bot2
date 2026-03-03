"""DB access is via Supabase client only. No SQLAlchemy engine/session."""
from app.supabase_async import check_connection

__all__ = ["check_connection"]
