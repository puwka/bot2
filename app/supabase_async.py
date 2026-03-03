"""Run sync Supabase client calls in thread pool so they don't block the event loop."""
import asyncio
from typing import TypeVar, Callable, Awaitable

from app.supabase_client import supabase

T = TypeVar("T")


async def run_sync(fn: Callable[[], T]) -> T:
    return await asyncio.to_thread(fn)


async def check_connection(timeout_seconds: float = 15.0) -> None:
    """Raises on connection/auth error."""
    def _check():
        supabase.table("users").select("id").limit(1).execute()
    await asyncio.wait_for(run_sync(_check), timeout=timeout_seconds)
