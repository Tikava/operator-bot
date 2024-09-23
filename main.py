from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy.exc import IntegrityError

import ssl

import aiohttp

from dotenv import load_dotenv

from database import session_scope, User as UserModel, Bot as BotModel, Chat as ChatModel

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


import asyncio
from os import getenv

load_dotenv()

dp = Dispatcher()
BOT_TOKEN = getenv("BOT_TOKEN")
SERVICE_URL = getenv("SERVICE_URL")
bot = Bot(token=BOT_TOKEN)

bot_form_router = Router()

class CustomCallback(CallbackData, prefix='id'):
    bot_id: int

class SUPPORT_BOT(StatesGroup):
    token = State()

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
        
async def set_webhook(user_answer):
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{SERVICE_URL}/setWebhook', json={'token': user_answer}, ssl=ssl_context) as response:
            return await response.json()
        
async def fetch_all(urls):
    tasks = [fetch(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    with session_scope() as session:
        user = session.query(UserModel).filter(UserModel.telegram_id == message.from_user.id).first()

    if user:
        await message.answer('Вы уже вы зарегистрированы.')
    else:
        with session_scope() as session:
            new_user = UserModel(telegram_id=message.from_user.id)
            session.add(new_user)

        await state.set_state(SUPPORT_BOT.token)
        await message.answer("Чтобы создать бота мне нужен токен, пожалуйста отправьте мне его. Токен можно получить у @BotFather.")

@bot_form_router.message(SUPPORT_BOT.token)
async def token_input_handler(message: Message, state: FSMContext) -> None:
    user_answer = message.text
    response = await fetch(f"https://api.telegram.org/bot{user_answer}/getMe")
    if response['ok']:
        with session_scope() as session:
            try: 
                new_bot = BotModel(token=user_answer, user_id=message.from_user.id)
                session.add(new_bot)
                session.commit()
            except IntegrityError as e:
                session.rollback()
                await state.set_state(SUPPORT_BOT.token)
                await message.answer('Токен уже используется. Попробуйте снова.')
                return

        await state.clear()
        await set_webhook(user_answer)
        await message.answer('Ваш бот успешно привязан!')
    else:
        await state.set_state(SUPPORT_BOT.token)
        await message.answer('Не верный токен! Попробуйте снова.')


@dp.message(Command('add_bot'))
async def add_bot_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(SUPPORT_BOT.token)
    await message.answer('Пожалуйста, введите токен бота от @BotFather.')

@dp.message(Command('my_bots'))
async def view_bots_handler(message: Message, state: FSMContext) -> None:
    with session_scope() as session:
        bots = session.query(BotModel).filter(BotModel.user_id == message.from_user.id).all()
    
        if bots:
            urls = [f"https://api.telegram.org/bot{bot.token}/getMe" for bot in bots]
            responses = await fetch_all(urls)
            inline_keyboard = [[InlineKeyboardButton(text=response['result']['first_name'], callback_data=CustomCallback(bot_id=response['result']['id']).pack())] for response in responses]
            markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

            await message.answer('Список ботов:', reply_markup=markup)
        else:
            await message.answer('У вас нет привязанных ботов.')

@dp.callback_query(CustomCallback.filter(F.bot_id))
async def handle_telegram_id(query: CallbackQuery, callback_data: CustomCallback) -> None:
    await query.message.edit_text('К этому боту не привязана группа.')

async def main() -> None:
    dp.include_router(bot_form_router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())