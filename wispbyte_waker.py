import asyncio

import config


# Не даёт виспбайту засыпить сервак
async def waker(t, bot):
    while True:
        await asyncio.sleep(t)
        await bot.send_chat_action(chat_id=config.OWNER_ID, action="typing")
