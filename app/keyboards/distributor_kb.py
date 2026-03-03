from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.dto import VideoDistributionDto


def task_keyboard(dist: VideoDistributionDto) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📎 Отправить ссылку", callback_data=f"dist:submit:{dist.id}")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")],
        ]
    )


def active_tasks_keyboard(tasks: list[VideoDistributionDto]) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"📹 {(t.video.url[:40] + '...' if t.video and t.video.url else str(t.id))}",
                callback_data=f"dist:task_detail:{t.id}",
            )
        ]
        for t in tasks
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
