import uuid

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.dto import UserRole
from app.services.admin_service import AdminService
from app.keyboards.common import main_menu_keyboard, cancel_keyboard, back_to_menu_keyboard
from app.keyboards.admin_kb import role_select_keyboard, topics_keyboard, stats_menu_keyboard, users_keyboard
from app.handlers.states import (
    AdminCreateTopic,
    AdminCreateUser,
    AdminAssignRole,
    AdminAssignCategory,
    AdminStatsUser,
    AdminReassign,
)

router = Router(name="admin")


def _admin_guard(user_role: UserRole | None) -> bool:
    return user_role == UserRole.ADMIN


# ── Create Topic ──────────────────────────────────────────

@router.callback_query(F.data == "admin:create_topic")
async def cb_create_topic(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminCreateTopic.waiting_name)
    await callback.message.edit_text("Введите название новой категории:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminCreateTopic.waiting_name)
async def msg_create_topic_name(message: Message, state: FSMContext, user_role: UserRole | None):
    if not _admin_guard(user_role):
        return
    name = message.text.strip()
    svc = AdminService()
    try:
        topic = await svc.create_topic(name, message.from_user.id)
        await message.answer(
            f"✅ Категория «{topic.name}» создана.",
            reply_markup=main_menu_keyboard(user_role),
        )
    except ValueError as e:
        await message.answer(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()


# ── Create User ───────────────────────────────────────────

@router.callback_query(F.data == "admin:create_user")
async def cb_create_user(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminCreateUser.waiting_telegram_id)
    await callback.message.edit_text("Введите Telegram ID нового пользователя:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminCreateUser.waiting_telegram_id)
async def msg_create_user_tgid(message: Message, state: FSMContext, user_role: UserRole | None):
    if not _admin_guard(user_role):
        return
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введите числовой Telegram ID.", reply_markup=cancel_keyboard())
        return
    await state.update_data(new_tg_id=tg_id)
    await state.set_state(AdminCreateUser.waiting_role)
    await message.answer("Выберите роль:", reply_markup=role_select_keyboard())


@router.callback_query(AdminCreateUser.waiting_role, F.data.startswith("role_select:"))
async def cb_create_user_role(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    role_value = callback.data.split(":")[1]
    role = UserRole(role_value)
    data = await state.get_data()
    tg_id = data["new_tg_id"]

    svc = AdminService()
    try:
        user = await svc.create_user(tg_id, role, callback.from_user.id)
        await callback.message.edit_text(
            f"✅ Пользователь создан:\n"
            f"Telegram ID: {user.telegram_id}\n"
            f"Роль: {user.role.value}",
            reply_markup=main_menu_keyboard(user_role),
        )
    except ValueError as e:
        await callback.message.edit_text(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()
    await callback.answer()


# ── Assign Role ───────────────────────────────────────────

@router.callback_query(F.data == "admin:assign_role")
async def cb_assign_role(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = AdminService()
    users = await svc.list_users()
    if not users:
        await callback.message.edit_text("Нет пользователей.", reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return
    await state.set_state(AdminAssignRole.waiting_user)
    await callback.message.edit_text("Выберите пользователя:", reply_markup=users_keyboard(users, "assign_role_user"))
    await callback.answer()


@router.callback_query(AdminAssignRole.waiting_user, F.data.startswith("assign_role_user:"))
async def cb_assign_role_user(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    if not _admin_guard(user_role):
        return
    tg_id = int(callback.data.split(":")[1])
    await state.update_data(target_tg_id=tg_id)
    await state.set_state(AdminAssignRole.waiting_role)
    await callback.message.edit_text("Выберите новую роль:", reply_markup=role_select_keyboard())
    await callback.answer()


@router.callback_query(AdminAssignRole.waiting_role, F.data.startswith("role_select:"))
async def cb_assign_role_confirm(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    role_value = callback.data.split(":")[1]
    role = UserRole(role_value)
    data = await state.get_data()
    tg_id = data["target_tg_id"]

    svc = AdminService()
    try:
        user = await svc.assign_role(tg_id, role, callback.from_user.id)
        await callback.message.edit_text(
            f"✅ Роль обновлена:\n"
            f"Пользователь: {user.telegram_id}\n"
            f"Новая роль: {user.role.value}",
            reply_markup=main_menu_keyboard(user_role),
        )
    except ValueError as e:
        await callback.message.edit_text(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()
    await callback.answer()


# ── Assign Category ───────────────────────────────────────

@router.callback_query(F.data == "admin:assign_category")
async def cb_assign_category(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = AdminService()
    users = await svc.list_users()
    if not users:
        await callback.message.edit_text("Нет пользователей.", reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return
    await state.set_state(AdminAssignCategory.waiting_user)
    await callback.message.edit_text(
        "Выберите пользователя:", reply_markup=users_keyboard(users, "assign_cat_user")
    )
    await callback.answer()


@router.callback_query(AdminAssignCategory.waiting_user, F.data.startswith("assign_cat_user:"))
async def cb_assign_cat_user(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    tg_id = int(callback.data.split(":")[1])
    await state.update_data(target_tg_id=tg_id)
    svc = AdminService()
    topics = await svc.list_topics()
    if not topics:
        await callback.message.edit_text("Нет категорий.", reply_markup=main_menu_keyboard(user_role))
        await state.clear()
        await callback.answer()
        return
    await state.set_state(AdminAssignCategory.waiting_topic)
    await callback.message.edit_text("Выберите категорию:", reply_markup=topics_keyboard(topics, "assign_cat_topic"))
    await callback.answer()


@router.callback_query(AdminAssignCategory.waiting_topic, F.data.startswith("assign_cat_topic:"))
async def cb_assign_cat_topic(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    topic_id = uuid.UUID(callback.data.split(":")[1])
    data = await state.get_data()
    tg_id = data["target_tg_id"]

    svc = AdminService()
    try:
        await svc.assign_category(tg_id, topic_id, callback.from_user.id)
        await callback.message.edit_text(
            "✅ Категория назначена.", reply_markup=main_menu_keyboard(user_role)
        )
    except ValueError as e:
        await callback.message.edit_text(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()
    await callback.answer()


# ── Statistics ────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def cb_stats_menu(callback: CallbackQuery, user_role: UserRole | None):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("📊 Статистика:", reply_markup=stats_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:stats_general")
async def cb_stats_general(callback: CallbackQuery,  user_role: UserRole | None):
    if not _admin_guard(user_role):
        return
    svc = AdminService()
    s = await svc.get_stats()
    text = (
        "📊 <b>Общая статистика</b>\n\n"
        f"Всего видео: {s.total_videos}\n"
        f"Всего распределено: {s.total_distributed}\n"
        f"Завершённых задач: {s.completed_tasks}\n"
        f"Отправлено ссылок: {s.total_links}\n"
        f"Всего пользователей: {s.total_users}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:stats_user")
async def cb_stats_user_select(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    svc = AdminService()
    users = await svc.list_users()
    await state.set_state(AdminStatsUser.waiting_user)
    await callback.message.edit_text(
        "Выберите пользователя:", reply_markup=users_keyboard(users, "stats_user_sel")
    )
    await callback.answer()


@router.callback_query(AdminStatsUser.waiting_user, F.data.startswith("stats_user_sel:"))
async def cb_stats_user_detail(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _admin_guard(user_role):
        return
    tg_id = int(callback.data.split(":")[1])
    svc = AdminService()
    try:
        us = await svc.get_user_stats(tg_id)
        text = (
            f"👤 <b>Статистика пользователя</b>\n\n"
            f"Telegram ID: {us['telegram_id']}\n"
            f"Username: {us['username'] or '—'}\n"
            f"Роль: {us['role']}\n"
            f"Всего задач: {us['total_assigned']}\n"
            f"Завершено: {us['completed']}"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    except ValueError as e:
        await callback.message.edit_text(f"⚠️ {e}", reply_markup=back_to_menu_keyboard())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin:stats_category")
async def cb_stats_category(callback: CallbackQuery,  user_role: UserRole | None):
    if not _admin_guard(user_role):
        return
    svc = AdminService()
    cats = await svc.get_category_stats()
    if not cats:
        await callback.message.edit_text("Нет категорий.", reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return
    lines = ["📁 <b>Статистика по категориям</b>\n"]
    for c in cats:
        lines.append(f"• {c['topic_name']}: {c['video_count']} видео")
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    await callback.answer()


# ── Unfinished Tasks ──────────────────────────────────────

@router.callback_query(F.data == "admin:unfinished")
async def cb_unfinished(callback: CallbackQuery, user_role: UserRole | None):
    if not _admin_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = AdminService()
    tasks = await svc.get_unfinished_tasks()
    if not tasks:
        await callback.message.edit_text("Все задачи завершены ✅", reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return
    lines = ["⏳ <b>Незавершённые задачи</b>\n"]
    for t in tasks[:20]:
        user_info = f"user={t.user.telegram_id}" if t.user else "?"
        video_url = t.video.url[:40] if t.video else "?"
        lines.append(f"• {video_url}… → {user_info}\n  ID: <code>{t.id}</code>")
    if len(tasks) > 20:
        lines.append(f"\n… и ещё {len(tasks) - 20}")
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=back_to_menu_keyboard())
    await callback.answer()
