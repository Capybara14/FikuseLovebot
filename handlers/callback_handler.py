import html

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd, successfully_create
from handlers.pm_commands_handler import create_command
from keyboards.pm_mode_keyboards import back_cmd_menu_keyboard, commands_keyboard, choose_chat_keyboard, \
    chat_commands_keyboard, back_chat_menu_keyboard
from keyboards.inline_mode_keyboards import response_keyboard
from utils.gender import gender_match_text
from utils.menus import chat_menu, cmd_menu
from utils.text import html_link_to_user

callback_handler_router = Router()


# 1. Кнопки из инлайн-сообщений (в любом чате)
@callback_handler_router.callback_query(F.inline_message_id, F.data.startswith("btn_"))
async def inline_buttons_handler(call: types.CallbackQuery, storage, bot):
    parts = call.data.split(" ")
    if parts[0] == "btn_accept":
        cmd_id = parts[1]
        author_msg_user_id = parts[2]
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        author_msg_first_name = storage.users_cache[author_msg_user_id].get("user_first_name",
                                                                            None) or author_msg_user_name or author_msg_user_id
        author_msg_gender = storage.users_cache[author_msg_user_id].get("gender")
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = cmd["title"].split()[0] + " | "
        if str(call.from_user.id) != parts[2]:
            storage.increment_uses(cmd_id)
            text = (
                f'{emoji}{html_link_to_user(author_msg_user_id, author_msg_user_name)}'
                f"{html.escape(author_msg_first_name)}</a> "
                f"{gender_match_text(cmd['text_response'], author_msg_gender)} "
                f'{html_link_to_user(call.from_user.id, call.from_user.username)}'
                f"{html.escape(call.from_user.first_name)}</a>"
            )
            await call.bot.edit_message_text(
                text=text,
                inline_message_id=call.inline_message_id,
                reply_markup=response_keyboard(author_msg_user_name),
                parse_mode="HTML",
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )

    elif parts[0] == "btn_deny":
        cmd_id = parts[1]
        author_msg_user_id = parts[2]
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        user_gender = storage.users_cache[str(call.from_user.id)].get("gender")
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = "❌ | "
        if str(call.from_user.id) != parts[2]:
            storage.increment_uses(cmd_id)
            text = (
                f'{emoji}{html_link_to_user(call.from_user.id, call.from_user.username)}'
                f"{html.escape(call.from_user.first_name)}</a> "
                f"{gender_match_text(cmd['text_deny'], user_gender)}"
            )
            await call.bot.edit_message_text(
                text=text,
                inline_message_id=call.inline_message_id,
                reply_markup=response_keyboard(author_msg_user_name),
                parse_mode="HTML",
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )


# 2. Кнопки из обычных сообщений в ЛС
@callback_handler_router.callback_query(F.message, F.data.startswith("btn_"))
async def pm_buttons_handler(call: types.CallbackQuery, storage, state: FSMContext, bot):
    parts = call.data.split(" ")
    if parts[0] == "btn_add_command":
        await create_command(message=call.message, storage=storage, state=state, bot=bot)

    elif parts[0] == "btn_all_right":
        await successfully_create(call, bot)

    elif parts[0] == "btn_cmd_page":
        target_id = parts[1]
        page = int(parts[2])
        await cmd_menu(call.message.message_id, call.message, bot, storage, target_id=target_id, page=page)
        await call.answer()

    elif parts[0] == "btn_back_cmd_menu":
        await state.clear()
        bot_message_id = call.message.message_id
        if len(parts) > 2:
            cmd_id = parts[2]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = storage.find_cmd(cmd_id)
            if not cmd: return
            storage.commands_cache[author_cmd_id].remove(cmd)
        if len(parts) > 1:
            bot_message_id = parts[1]
        await cmd_menu(bot_message_id, call.message, bot, storage)

    elif parts[0] == "btn_delete_command":
        try:
            cmd_id = parts[1]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = storage.find_cmd(cmd_id)
            if not cmd: return
            storage.commands_cache[author_cmd_id].remove(cmd)
            text = f"✅ *Команда успешно удалена*"
        except:
            text = "❌ Ошибка удаления команды"
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=back_cmd_menu_keyboard(call.message.message_id),
            parse_mode="Markdown")

    elif parts[0] == "btn_gender":
        gender = parts[1]
        if gender == "None":
            gender = "Мужской"
        elif gender == "Мужской":
            gender = "Женский"
        elif gender == "Женский":
            gender = "Мужской"
        storage.users_cache[str(call.from_user.id)]["gender"] = gender
        page = int(parts[2]) if len(parts) > 2 else 0
        await call.message.edit_reply_markup(
            reply_markup=commands_keyboard(str(call.from_user.id), storage, page=page)
        )

    elif parts[0] == "btn_delete_chat_command":
        chat_id = parts[1]
        cmd_id = parts[2]
        text = "❌ Ошибка удаления команды"
        cmds = storage.chats_cache.get(chat_id, {}).get("cmds", {})
        for trigger, value in cmds.items():
            if value == cmd_id:
                del cmds[trigger]
                text = "✅ *Команда успешно удалена*"
                break
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=back_chat_menu_keyboard(call.message.message_id, chat_id),
            parse_mode="Markdown")

    elif parts[0] == "btn_chat_cmd_choose":
        chat_id = parts[1]
        bot_message_id = parts[2]
        chat = await bot.get_chat(chat_id)
        title = chat.title or f"{chat_id}"
        await chat_menu(bot_message_id, chat_id, title, storage, call.message, bot)

    elif parts[0] == "btn_back_to_chat_choose":
        bot_message_id = parts[1]
        chats = storage.users_cache[str(call.from_user.id)].get("chats")
        if chats is not None and len(chats) > 0:
            await bot.edit_message_text("*Выберите чат для настройки: *", chat_id=call.message.chat.id,
                                        message_id=bot_message_id,
                                        parse_mode="Markdown",
                                        reply_markup=await choose_chat_keyboard(chats, bot_message_id, bot,
                                                                                storage))
        else:
            await bot.edit_message_text("❗ Вы не являетесь админом ни одного из чатов, где есть бот",
                                        chat_id=call.message.chat.id,
                                        message_id=bot_message_id, parse_mode="Markdown")
    await call.answer()




