import config
from keyboards.pm_mode_keyboards import commands_keyboard, chat_commands_keyboard


async def cmd_menu(bot_message_id, message, bot, storage, target_id=None):
    if target_id is None:
        target_id = str(message.chat.id)
    if storage.commands_cache.get(target_id, None) is None or len(
            storage.commands_cache[target_id]) == 0:
        text = "❗ *У вас ещё нет команд, выберите действие*"
    else:
        text = f"*📋 Ваши команды:*\n\n"
        for cmd in storage.commands_cache[target_id]:
            text += f"   — {cmd["title"]} ([Детали](https://t.me/{config.BOT_USERNAME}?start=mycmd_{cmd["id"]}_{bot_message_id}))\n\n"
        text += f" "

    await bot.edit_message_text(
        text=text,
        chat_id=message.chat.id,
        message_id=int(bot_message_id),
        reply_markup=commands_keyboard(user_id=target_id, storage=storage),
        parse_mode="Markdown")


async def chat_menu(bot_message_id, chat_id, title, storage, message, bot):
    cmds = storage.chats_cache.get(chat_id, {}).get("cmds", {})
    lines = []
    for cmd_trigger, cmd_id in list(cmds.items()):
        cmd = storage.find_cmd(cmd_id)
        if cmd is None:
            cmds.pop(cmd_trigger, None)
            continue
        lines.append(
            f"   — {cmd_trigger} ([Детали](https://t.me/{config.BOT_USERNAME}?start=chatcmd_{cmd["id"]}_{chat_id}_{bot_message_id}))\n\n"
        )

    if not lines:
        text = "❗ *В чате ещё нет команд, выберите действие*"
    else:
        text = f"*Команды чата {title}:*\n\n" + "".join(lines) + " "

    await bot.edit_message_text(
        text=text,
        chat_id=message.chat.id,
        message_id=int(bot_message_id),
        reply_markup=chat_commands_keyboard(bot_message_id, chat_id),
        parse_mode="Markdown")
