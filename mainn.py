
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

#
BOT_TOKEN = "8425206037:AAHocGEFY_DuQFPqDanixjBkj0VvcjD7SkM"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


class AuthStates(StatesGroup):
    waiting_for_contact = State()


def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться номером", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_refresh_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить ссылку", callback_data="get_link")]
    ])


@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await message.answer(
        "Привет! Для входа поделись своим номером телефона.",
        reply_markup=get_contact_keyboard()
    )
    await state.set_state(AuthStates.waiting_for_contact)


@router.message(AuthStates.waiting_for_contact, lambda m: m.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    await state.update_data(phone=contact.phone_number)

    if contact.user_id != message.from_user.id:
        await message.answer(
            "Этот номер не принадлежит вам! Пожалуйста, поделитесь своим контактом.",
            reply_markup=get_contact_keyboard()
        )
        return

    await message.answer(
        "Номер подтверждён!",
        reply_markup=types.ReplyKeyboardRemove()
    )

    now = datetime.now(timezone.utc)
    auth_link = f"https://example.com/auth?phone={contact.phone_number}&t={int(now.timestamp())}"

    await message.answer(
        f"Ссылка для входа (действует 1 минуту):\n{auth_link}",
        reply_markup=get_refresh_button()
    )

    await state.update_data(
        link_issued_at=now,
        verified=True
    )


@router.callback_query(lambda c: c.data == "get_link")
async def refresh_link(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone")

    if not phone:
        await callback.message.answer("Сессия истекла или данных нет. Начните заново: /start")
        await state.clear()
        await callback.answer()
        return

    issued_at = data.get("link_issued_at")
    now = datetime.now(timezone.utc)

    if not issued_at:
        issued_at = now - timedelta(minutes=10)

    expired = now - issued_at > timedelta(minutes=1)

    if expired:
        new_token = int(now.timestamp())
        new_link = f"https://example.com/auth?phone={phone}&t={new_token}"

        await callback.message.edit_text(
            f"⏰ Время ссылки истекло.\nНовая ссылка (действует 1 минуту):\n{new_link}",
            reply_markup=get_refresh_button()
        )

        await state.update_data(link_issued_at=now)
        await callback.answer("Ссылка обновлена!")

    else:
        await callback.answer(
            "Ссылка ещё действительна. Подождите окончания срока.",
            show_alert=True
        )


@router.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Сессия сброшена. Напиши /start для начала заново.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())