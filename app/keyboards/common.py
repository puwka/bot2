from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.dto import UserRole


def main_menu_keyboard(role: UserRole | None) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    if role == UserRole.ADMIN:
        buttons.append([InlineKeyboardButton(text="📂 Создать категорию", callback_data="admin:create_topic")])
        buttons.append([InlineKeyboardButton(text="👤 Создать пользователя", callback_data="admin:create_user")])
        buttons.append([InlineKeyboardButton(text="🔑 Назначить роль", callback_data="admin:assign_role")])
        buttons.append([InlineKeyboardButton(text="📁 Назначить категории", callback_data="admin:assign_category")])
        buttons.append([InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")])
        buttons.append([InlineKeyboardButton(text="⏳ Незавершённые задачи", callback_data="admin:unfinished")])

    if role == UserRole.UPLOADER:
        buttons.append([InlineKeyboardButton(text="📤 Загрузить видео", callback_data="uploader:add_video")])

    if role == UserRole.DISTRIBUTOR:
        buttons.append([InlineKeyboardButton(text="🎬 Получить видео", callback_data="dist:get_video")])
        buttons.append([InlineKeyboardButton(text="📋 Мои задачи", callback_data="dist:my_tasks")])

    if not buttons:
        buttons.append([InlineKeyboardButton(text="ℹ️ Нет доступа", callback_data="noop")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )
