import io
import uuid

from aiogram import Bot, F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.dto import UserRole
from app.services.uploader_service import UploaderService
from app.services.admin_service import AdminService
from app.keyboards.common import main_menu_keyboard, cancel_keyboard
from app.keyboards.admin_kb import topics_keyboard
from app.handlers.states import UploaderAddVideo

router = Router(name="uploader")


def _uploader_guard(user_role: UserRole | None) -> bool:
    return user_role == UserRole.UPLOADER


@router.callback_query(F.data == "uploader:add_video")
async def cb_add_video(
    callback: CallbackQuery, state: FSMContext, user_role: UserRole | None
):
    if not _uploader_guard(user_role):
        await callback.answer("Нет доступа", show_alert=True)
        return
    svc = AdminService()
    topics = await svc.list_topics()
    if not topics:
        await callback.message.edit_text(
            "Нет категорий. Обратитесь к админу.",
            reply_markup=main_menu_keyboard(user_role),
        )
        await callback.answer()
        return
    await state.set_state(UploaderAddVideo.waiting_topic)
    await callback.message.edit_text(
        "Выберите категорию видео:",
        reply_markup=topics_keyboard(topics, "upload_topic"),
    )
    await callback.answer()


@router.callback_query(UploaderAddVideo.waiting_topic, F.data.startswith("upload_topic:"))
async def cb_upload_topic(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    if not _uploader_guard(user_role):
        return
    topic_id = callback.data.split(":")[1]
    await state.update_data(topic_id=topic_id)
    await state.set_state(UploaderAddVideo.waiting_video)
    await callback.message.edit_text(
        "Отправьте видеофайл (видео или документ) или ссылку на видео:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(UploaderAddVideo.waiting_video, F.video)
async def msg_upload_video_file(
    message: Message, state: FSMContext, bot: Bot, user_role: UserRole | None
):
    if not _uploader_guard(user_role):
        return
    data = await state.get_data()
    topic_id = uuid.UUID(data["topic_id"])
    try:
        file = await bot.get_file(message.video.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        buf.seek(0)
        file_bytes = buf.getvalue()
    except Exception as e:
        await message.answer(f"⚠️ Не удалось скачать файл: {e}", reply_markup=main_menu_keyboard(user_role))
        await state.clear()
        return
    content_type = message.video.mime_type or "video/mp4"
    svc = UploaderService()
    try:
        video = await svc.add_video_file(
            file_bytes, content_type, topic_id, message.from_user.id, description=message.caption
        )
        await message.answer(
            f"✅ Видео загружено в папку категории на Яндекс.Диске (имя файла = код: <code>{getattr(video, 'content_code', '') or video.id}</code>).\nПлатформа: uploaded\nID: <code>{video.id}</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_role),
        )
    except Exception as e:
        err = str(e).lower()
        if "timeout" in err or "timed out" in err:
            await message.answer(
                "⚠️ Таймаут при загрузке. Файл мог загрузиться на Диск под временным именем — проверьте папку категории. Попробуйте загрузить снова или отправьте видео меньшего размера.",
                reply_markup=main_menu_keyboard(user_role),
            )
        elif "ssl" in err or "connect" in err or "eof" in err or "protocol" in err:
            await message.answer(
                "⚠️ Ошибка сети при загрузке на Яндекс.Диск. Проверьте интернет и VPN/прокси, затем попробуйте снова.",
                reply_markup=main_menu_keyboard(user_role),
            )
        elif "507" in err or "insufficient storage" in err:
            await message.answer(
                "⚠️ Недостаточно места на Яндекс.Диске. Освободите место в аккаунте, с которым получен токен.",
                reply_markup=main_menu_keyboard(user_role),
            )
        else:
            await message.answer(
                "⚠️ Ошибка: " + str(e).replace("<", " ").replace(">", " "),
                reply_markup=main_menu_keyboard(user_role),
            )
    await state.clear()


@router.message(UploaderAddVideo.waiting_video, F.document)
async def msg_upload_document_video(
    message: Message, state: FSMContext, bot: Bot, user_role: UserRole | None
):
    if not _uploader_guard(user_role):
        return
    mime = (message.document.mime_type or "").lower()
    if not mime.startswith("video/"):
        await message.answer(
            "⚠️ Отправьте видеофайл или ссылку на видео.",
            reply_markup=cancel_keyboard(),
        )
        return
    data = await state.get_data()
    topic_id = uuid.UUID(data["topic_id"])
    try:
        file = await bot.get_file(message.document.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        buf.seek(0)
        file_bytes = buf.getvalue()
    except Exception as e:
        await message.answer(f"⚠️ Не удалось скачать файл: {e}", reply_markup=main_menu_keyboard(user_role))
        await state.clear()
        return
    content_type = message.document.mime_type or "video/mp4"
    svc = UploaderService()
    try:
        video = await svc.add_video_file(
            file_bytes, content_type, topic_id, message.from_user.id, description=message.caption
        )
        await message.answer(
            f"✅ Видео загружено в папку категории на Яндекс.Диске (имя файла = код: <code>{getattr(video, 'content_code', '') or video.id}</code>).\nПлатформа: uploaded\nID: <code>{video.id}</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_role),
        )
    except Exception as e:
        err = str(e).lower()
        if "timeout" in err or "timed out" in err:
            await message.answer(
                "⚠️ Таймаут при загрузке. Файл мог загрузиться на Диск под временным именем — проверьте папку категории. Попробуйте загрузить снова или отправьте видео меньшего размера.",
                reply_markup=main_menu_keyboard(user_role),
            )
        elif "ssl" in err or "connect" in err or "eof" in err or "protocol" in err:
            await message.answer(
                "⚠️ Ошибка сети при загрузке на Яндекс.Диск. Проверьте интернет и VPN/прокси, затем попробуйте снова.",
                reply_markup=main_menu_keyboard(user_role),
            )
        elif "507" in err or "insufficient storage" in err:
            await message.answer(
                "⚠️ Недостаточно места на Яндекс.Диске. Освободите место в аккаунте, с которым получен токен.",
                reply_markup=main_menu_keyboard(user_role),
            )
        else:
            await message.answer(
                "⚠️ Ошибка: " + str(e).replace("<", " ").replace(">", " "),
                reply_markup=main_menu_keyboard(user_role),
            )
    await state.clear()


@router.message(UploaderAddVideo.waiting_video, F.text)
async def msg_upload_link(message: Message, state: FSMContext, user_role: UserRole | None):
    if not _uploader_guard(user_role):
        return
    url = message.text.strip()
    if not url.startswith("http"):
        await message.answer(
            "⚠️ Отправьте видеофайл или корректную ссылку на видео.",
            reply_markup=cancel_keyboard(),
        )
        return
    await state.update_data(url=url)
    await state.set_state(UploaderAddVideo.waiting_description)
    await message.answer(
        "Добавьте описание (или отправьте «—» чтобы пропустить):",
        reply_markup=cancel_keyboard(),
    )


@router.message(UploaderAddVideo.waiting_description, F.text)
async def msg_upload_description(
    message: Message, state: FSMContext, user_role: UserRole | None
):
    """Описание только для добавления по ссылке (не для файла)."""
    if not _uploader_guard(user_role):
        return
    data = await state.get_data()
    description_text = (message.text or "").strip()
    description = None if description_text in ("—", "-", "") else description_text
    svc = UploaderService()
    try:
        video = await svc.add_video_by_link(
            url=data["url"],
            topic_id=uuid.UUID(data["topic_id"]),
            telegram_id=message.from_user.id,
            description=description,
        )
        await message.answer(
            f"✅ Видео добавлено!\nПлатформа: {video.platform}\nID: <code>{video.id}</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_role),
        )
    except ValueError as e:
        await message.answer(f"⚠️ {e}", reply_markup=main_menu_keyboard(user_role))
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}", reply_markup=main_menu_keyboard(user_role))
    await state.clear()
