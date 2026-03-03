from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.dto import UserRole, UserDto
from app.keyboards.common import main_menu_keyboard

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: UserDto | None, user_role: UserRole | None):
    if not db_user:
        await message.answer(
            "⚠️ Вы не зарегистрированы в системе.\n"
            "Обратитесь к администратору для получения доступа."
        )
        return
    await message.answer(
        f"Добро пожаловать, {db_user.full_name or db_user.username or db_user.telegram_id}!\n"
        f"Ваша роль: {db_user.role.value}",
        reply_markup=main_menu_keyboard(user_role),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(user_role),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext, user_role: UserRole | None):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=main_menu_keyboard(user_role),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer("Нет доступных действий", show_alert=True)
