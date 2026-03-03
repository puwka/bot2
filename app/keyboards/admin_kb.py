from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.dto import UserRole


def role_select_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=r.value, callback_data=f"role_select:{r.value}")]
        for r in UserRole
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topics_keyboard(topics: list, action_prefix: str = "topic_select") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=t.name, callback_data=f"{action_prefix}:{t.id}")]
        for t in topics
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def stats_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin:stats_general")],
            [InlineKeyboardButton(text="👤 Статистика по пользователю", callback_data="admin:stats_user")],
            [InlineKeyboardButton(text="📁 Статистика по категориям", callback_data="admin:stats_category")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
        ]
    )


def users_keyboard(users: list, action_prefix: str = "user_select") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{u.username or u.telegram_id} ({u.role.value})",
                callback_data=f"{action_prefix}:{u.telegram_id}",
            )
        ]
        for u in users
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
