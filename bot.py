import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer("Бот работает ✅")

@dp.message(Command("help"))
async def help_cmd(msg: Message):
    await msg.answer("Команды: /start /help")

async def main():
    await dp.start_polling(bot)

asyncio.run(main())
