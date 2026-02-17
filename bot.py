from aiogram import Bot, Dispatcher
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(TOKEN)
dp = Dispatcher(bot)

async def main():
    print("Бот стартует")
    await asyncio.sleep(5)
    print("Бот завершает работу")

asyncio.run(main())
