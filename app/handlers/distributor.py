import logging
import uuid

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.dto import UserRole
from app.services.distributor_service import DistributorService
from app.supabase_async import run_sync
from app.keyboards.common import main_menu_keyboard, cancel_keyboard
from app.keyboards.distributor_kb import task_keyboard, active_tasks_keyboard
from app.handlers.states import DistSubmitResult

logger = logging.getLogger(__name__)

router = Router(name="distributor")


def _dist_guard(user_role: UserRole | None) -> bool:
    return user_role == UserRole.DISTRIBUTOR


# ── Get Video ─────────────────────────────────────────────

@router.callback_query(F.data == "dist:get_video")
async def cb_get_video(callback: CallbackQuery, user_role: UserRole | None):
    if not _dist_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = DistributorService()
    # Максимум 1 активная задача: новое видео только после отправки ссылки по текущей
    active = await svc.get_active_tasks(callback.from_user.id)
    if active:
        await callback.message.edit_text(
            "У вас уже есть активная задача. Сначала отправьте ссылку на видео (кнопка «Отправить ссылку» в сообщении с задачей), затем вы сможете получить следующее видео.",
            reply_markup=main_menu_keyboard(user_role),
        )
        await callback.answer()
        return
    try:
        dist = await svc.get_next_video(callback.from_user.id)
    except ValueError as e:
        await callback.message.edit_text(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return

    if not dist:
        user = await svc.user_repo.get_by_telegram_id(callback.from_user.id)
        stats = await svc.dist_repo.get_availability_stats(user.id) if user else None
        if stats and stats[1] > 0:
            total, received = stats
            msg = (
                f"По вашим категориям вы уже получили все доступные видео ({received} шт.).\n\n"
                f"Когда в папках на Яндекс.Диске появятся новые файлы, нажмите «Получить видео» ещё раз — они подтянутся автоматически."
            )
        else:
            msg = "Нет доступных видео в ваших категориях. Добавьте файлы в папки на Яндекс.Диске по вашим категориям и нажмите «Получить видео» снова."
        await callback.message.edit_text(msg, reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return

    video = dist.video
    drive_id = getattr(video, "drive_file_id", None) if video else None
    platform = (video.platform or "—") if video else "—"
    desc = (video.description or "—") if video else "—"
    task_caption = (
        f"Платформа: {platform}\n"
        f"Описание: {desc}\n\n"
        f"ID задачи: <code>{dist.id}</code>"
    )

    # Ссылка на файл: приоритет — сохранённая публичная (video.url), иначе получаем/публикуем по пути
    drive_url = ""
    stored_url = (video.url or "").strip() if video else ""
    if stored_url and ("disk.yandex.ru/d/" in stored_url or "yadi.sk/" in stored_url):
        drive_url = stored_url
    if not drive_url and drive_id:
        path = str(drive_id).strip()
        if path:
            from app.yandex_disk_service import get_link_to_file
            drive_url = await run_sync(lambda: get_link_to_file(path))
    if not drive_url and stored_url:
        drive_url = stored_url

    # Выдаём только ссылку на видео (без скачивания и отправки файла)
    url = drive_url
    is_yandex = url and ("yandex" in url.lower() or "yadi.sk" in url.lower())
    link_title = "Ссылка на видео на Яндекс.Диске" if is_yandex else "Ссылка на видео"
    link_line = f'<a href="{url}">Открыть видео</a>' if url else "Ссылка недоступна"
    copy_line = f"\nСкопировать: <code>{url}</code>\n\n" if url else "\n\n"
    text = (
        f"🔗 <b>{link_title}</b>\n\n"
        f"{link_line}"
        f"{copy_line}"
        f"{task_caption}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=task_keyboard(dist))
    await callback.answer()


# ── My Tasks ──────────────────────────────────────────────

@router.callback_query(F.data == "dist:my_tasks")
async def cb_my_tasks(callback: CallbackQuery, user_role: UserRole | None):
    if not _dist_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = DistributorService()
    tasks = await svc.get_active_tasks(callback.from_user.id)
    if not tasks:
        await callback.message.edit_text("У вас нет активных задач.", reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return
    await callback.message.edit_text("📋 Ваши активные задачи:", reply_markup=active_tasks_keyboard(tasks))
    await callback.answer()


@router.callback_query(F.data.startswith("dist:task_detail:"))
async def cb_task_detail(callback: CallbackQuery, user_role: UserRole | None):
    if not _dist_guard(user_role):
        return
    dist_id = uuid.UUID(callback.data.split(":")[2])
    from app.repositories.distribution_repo import DistributionRepository

    repo = DistributionRepository()
    dist = await repo.get_by_id(dist_id)
    if not dist:
        await callback.message.edit_text("Задача не найдена.", reply_markup=main_menu_keyboard(user_role))
        await callback.answer()
        return
    video = dist.video
    url = video.url if video else "—"
    platform = (video.platform or "—") if video else "—"
    results_text = ""
    if dist.results:
        results_text = "\n\nОтправленные ссылки:\n" + "\n".join(f"• {r.url}" for r in dist.results)
    text = (
        f"🎬 <b>Задача</b>\n\n"
        f"Видео: {url}\n"
        f"Платформа: {platform}\n"
        f"Статус: {'✅ Завершена' if dist.completed else '⏳ В работе'}"
        f"{results_text}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=task_keyboard(dist))
    await callback.answer()


# ── Submit Result ─────────────────────────────────────────

@router.callback_query(F.data.startswith("dist:submit:"))
async def cb_submit_start(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    if not _dist_guard(user_role):
        return
    dist_id = callback.data.split(":")[2]
    await state.update_data(distribution_id=dist_id)
    await state.set_state(DistSubmitResult.waiting_url)
    # Кнопка может быть на сообщении с видео (без текста) — edit_text вызовет ошибку, отправляем новое сообщение
    await callback.message.answer(
        "Отправьте ссылку-результат:", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(DistSubmitResult.waiting_url)
async def msg_submit_url(
    message: Message, state: FSMContext, user_role: UserRole | None
):
    if not _dist_guard(user_role):
        return
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer("⚠️ Пожалуйста, отправьте корректную ссылку.", reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    dist_id = uuid.UUID(data["distribution_id"])

    svc = DistributorService()
    try:
        result = await svc.submit_result(dist_id, url, message.from_user.id)
        await message.answer(
            f"✅ Ссылка принята!\n"
            f"Платформа: {result.platform or '—'}\n\n"
            "Вы можете отправить ещё одну ссылку или вернуться в меню.",
            reply_markup=main_menu_keyboard(user_role),
        )
    except ValueError as e:
        await message.answer(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()
