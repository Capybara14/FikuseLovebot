import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from handlers import handler_router
from database.storage import Storage
import config

dp = Dispatcher()


@dp.startup()
async def on_startup(storage: Storage):
    dp["save_task"] = asyncio.create_task(storage.save_cache())



@dp.shutdown()
async def on_shutdown(storage: Storage):
    dp["save_task"].cancel()
    try:
        await dp["save_task"]
    except asyncio.CancelledError:
        pass
    await storage.save_cache(once=True)


async def main():
    bot = Bot(token=config.BOT_TOKEN)
    storage = Storage(config.FILE_USERS_PATH, config.FILE_COMMANDS_PATH, config.TIMEOUT)
    storage.load_cache()
    dp.include_router(handler_router)
    await bot.set_my_commands([
        BotCommand(command="my_commands", description="Мои команды"),
        BotCommand(command="help", description="Инструкция")
    ])
    await dp.start_polling(bot, storage=storage)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
