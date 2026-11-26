from aiogram.enums import ButtonStyle
from aiogram.types import InputRichBlockSectionHeading, InputRichMessage, InputRichBlockParagraph, \
    InputRichBlockButtons, rich_message_button, RichMessageButton, InputRichBlockTable, RichBlockTableCell, \
    RichTextButton

import config
from keyboards.callbacks import BtnCallback
from keyboards.pm_mode_keyboards import commands_keyboard, chat_commands_keyboard


async def cmd_menu(message, bot, storage, target_id=None, bot_message_id=None, page=0):
    if target_id is None:
        target_id = str(message.chat.id)
    cmds = storage.commands_cache.get(target_id) or []
    per_page = config.COMMANDS_PER_PAGE
    total_pages = max(1, (len(cmds) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    table = []
    if not cmds:
        head = InputRichBlockSectionHeading(size=1, text="❗ У вас ещё нет команд\n")
    else:
        head = InputRichBlockSectionHeading(size=1, text="📋 Ваши RP-команды:")
        page_cmds = cmds[page * per_page:(page + 1) * per_page]
        for cmd in page_cmds:
            table.append([
                RichBlockTableCell(text=cmd["title"], align="left", valign="middle"),
                RichBlockTableCell(
                    text=RichTextButton(button=RichMessageButton(text="Детали", style=ButtonStyle.PRIMARY,
                                                                 callback_data=BtnCallback(
                                                                     action="command_details").pack())),
                    align="right", valign="middle"),
            ])
        table = InputRichBlockTable(is_striped=True, cells=table)

    end = InputRichBlockButtons(buttons=[RichMessageButton(text="Создать команду", style=ButtonStyle.SUCCESS,
                                                           callback_data=BtnCallback(action="add_command").pack())])

    blocks = [head, table, end] if table else [head, end]

    if bot_message_id is not None:
        await bot.edit_message_text(
            rich_message=InputRichMessage(blocks=blocks),
            chat_id=message.chat.id,
            message_id=int(bot_message_id),
            reply_markup=commands_keyboard(user_id=target_id, storage=storage, page=page))
    else:
        await message.answer_rich(rich_message=InputRichMessage(blocks=blocks),
                             reply_markup=commands_keyboard(user_id=target_id, storage=storage, page=page))


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
