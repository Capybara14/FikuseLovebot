import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import wispbyte_waker
from handlers import handler_router
from database.storage import Storage
import config
from utils.cmd_bar import set_bot_commands
from utils.global_middleware import ban_middleware, save_user_middleware
from utils.global_middleware import AntiSpamMiddleware

dp = Dispatcher()


@dp.startup()
async def on_startup(storage: Storage, bot):
    dp["save_task"] = asyncio.create_task(storage.save_cache())
    dp["wake-up"] = asyncio.create_task(wispbyte_waker.waker(15, bot))


@dp.shutdown()
async def on_shutdown(storage: Storage, bot):
    dp["save_task"].cancel()
    dp["wake-up"].cancel()
    try:
        await dp["save_task"]
    except asyncio.CancelledError:
        pass
    await storage.save_cache(once=True)


async def main():
    bot = Bot(token=config.BOT_TOKEN)

    storage = Storage(config.FILE_USERS_PATH, config.FILE_COMMANDS_PATH, config.FILE_CHATS_PATH, config.TIMEOUT)
    storage.load_cache()

    dp.update.outer_middleware(ban_middleware)

    dp.update.outer_middleware(save_user_middleware)

    antispam = AntiSpamMiddleware()
    dp.message.outer_middleware(antispam)
    dp.callback_query.outer_middleware(antispam)

    dp.include_router(handler_router)

    await set_bot_commands(bot)

    await dp.start_polling(bot, storage=storage, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
