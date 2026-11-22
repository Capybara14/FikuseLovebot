from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats


async def set_bot_commands(bot):
    await bot.set_my_commands(
        [BotCommand(command="my_commands", description="Мои команды"),
         BotCommand(command="my_chats", description="Мои чаты"),
         BotCommand(command="help", description="Инструкция")],
        scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        [ # BotCommand(command="refresh", description="Обновить список админов"),
         BotCommand(command="chat_commands", description="Просмотреть команды чата")],
        scope=BotCommandScopeAllGroupChats()
    )
