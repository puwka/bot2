import uuid

from app.dto import UserDto, UserRole
from app.supabase_client import supabase
from app.supabase_async import run_sync


class UserRepository:
    def __init__(self, client=supabase):
        self._client = client

    async def get_by_telegram_id(self, telegram_id: int) -> UserDto | None:
        def _get():
            r = self._client.table("users").select("*").eq("telegram_id", telegram_id).execute()
            if r.data and len(r.data) > 0:
                return UserDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def get_by_id(self, user_id: uuid.UUID) -> UserDto | None:
        def _get():
            r = self._client.table("users").select("*").eq("id", str(user_id)).execute()
            if r.data and len(r.data) > 0:
                return UserDto.from_row(r.data[0])
            return None

        return await run_sync(_get)

    async def create(
        self,
        telegram_id: int,
        role: UserRole = UserRole.DISTRIBUTOR,
        username: str | None = None,
        full_name: str | None = None,
    ) -> UserDto:
        def _create():
            payload = {
                "telegram_id": telegram_id,
                "role": role.value,
                "username": username,
                "full_name": full_name,
            }
            r = self._client.table("users").insert(payload).execute()
            return UserDto.from_row(r.data[0])

        return await run_sync(_create)

    async def update_role(self, user_id: uuid.UUID, role: UserRole) -> UserDto | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        def _update():
            self._client.table("users").update({"role": role.value}).eq("id", str(user_id)).execute()
            return user  # return same with new role

        await run_sync(_update)
        return UserDto(user.id, user.telegram_id, user.username, user.full_name, role, user.is_active, user.performer_code, user.distributor_code)

    async def set_active(self, user_id: uuid.UUID, is_active: bool) -> UserDto | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        def _update():
            self._client.table("users").update({"is_active": is_active}).eq("id", str(user_id)).execute()

        await run_sync(_update)
        return UserDto(user.id, user.telegram_id, user.username, user.full_name, user.role, is_active, user.performer_code, user.distributor_code)

    async def list_all(self) -> list[UserDto]:
        def _list():
            r = self._client.table("users").select("*").order("created_at", desc=True).execute()
            return [UserDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)

    async def list_by_role(self, role: UserRole) -> list[UserDto]:
        def _list():
            r = self._client.table("users").select("*").eq("role", role.value).order("created_at", desc=True).execute()
            return [UserDto.from_row(row) for row in (r.data or [])]

        return await run_sync(_list)

    async def count_all(self) -> int:
        def _count():
            r = self._client.table("users").select("id", count="exact").execute()
            return r.count or 0

        return await run_sync(_count)
