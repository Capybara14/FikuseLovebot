import html

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd, successfully_create
from handlers.pm_commands_handler import create_command
from keyboards.callbacks import BtnCallback
from keyboards.pm_mode_keyboards import back_cmd_menu_keyboard, commands_keyboard, choose_chat_keyboard, \
    chat_commands_keyboard, back_chat_menu_keyboard
from keyboards.inline_mode_keyboards import response_keyboard
from utils.gender import gender_match_text
from utils.menus import chat_menu, cmd_menu
from utils.text import html_link_to_user

callback_handler_router = Router()


# 1. Кнопки из инлайн-сообщений (в любом чате)
@callback_handler_router.callback_query(F.inline_message_id, BtnCallback.filter())
async def inline_buttons_handler(call: types.CallbackQuery, callback_data: BtnCallback, storage, bot):
    if callback_data.action == "accept":
        cmd_id = callback_data.cmd_id
        author_msg_user_id = callback_data.user_id
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        author_msg_first_name = storage.users_cache[author_msg_user_id].get("user_first_name",
                                                                            None) or author_msg_user_name or author_msg_user_id
        author_msg_gender = storage.users_cache[author_msg_user_id].get("gender")
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = cmd["title"].split()[0] + " | "
        if str(call.from_user.id) != author_msg_user_id:
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

    elif callback_data.action == "deny":
        cmd_id = callback_data.cmd_id
        author_msg_user_id = callback_data.user_id
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        user_gender = storage.users_cache[str(call.from_user.id)].get("gender")
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = "❌ | "
        if str(call.from_user.id) != author_msg_user_id:
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
@callback_handler_router.callback_query(F.message, BtnCallback.filter())
async def pm_buttons_handler(call: types.CallbackQuery, callback_data: BtnCallback, storage, state: FSMContext, bot):
    if callback_data.action == "noop":
        await call.answer()
        return

    if callback_data.action == "delete_msg":
        await bot.delete_message(chat_id=call.message.chat.id, message_id=int(callback_data.message_id))
        await call.answer()
        return

    if callback_data.action == "add_command":
        await create_command(message=call.message, storage=storage, state=state)

    elif callback_data.action == "all_right":
        await successfully_create(call, bot)

    elif callback_data.action == "cmd_page":
        target_id = callback_data.user_id
        page = callback_data.page or 0
        await cmd_menu(bot_message_id=call.message.message_id, message=call.message, bot=bot, storage=storage,
                       target_id=target_id, page=page)
        await call.answer()

    elif callback_data.action == "back_cmd_menu":
        await state.clear()
        if callback_data.cmd_id:
            cmd_id = callback_data.cmd_id
            author_cmd_id = cmd_id.split("_")[0]
            cmd = storage.find_cmd(cmd_id)
            if not cmd: return
            storage.commands_cache[author_cmd_id].remove(cmd)
        await cmd_menu(bot_message_id=call.message.message_id, message=call.message, bot=bot, storage=storage)

    elif callback_data.action == "delete_command":
        try:
            cmd_id = callback_data.cmd_id
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
            text=text, reply_markup=back_cmd_menu_keyboard(),
            parse_mode="Markdown")

    elif callback_data.action == "gender":
        gender = callback_data.gender
        if not gender or gender == "None":
            gender = "Мужской"
        elif gender == "Мужской":
            gender = "Женский"
        elif gender == "Женский":
            gender = "Мужской"
        storage.users_cache[str(call.from_user.id)]["gender"] = gender
        page = callback_data.page if callback_data.page is not None else 0
        await call.message.edit_reply_markup(
            reply_markup=commands_keyboard(str(call.from_user.id), storage, page=page)
        )

    elif callback_data.action == "delete_chat_command":
        chat_id = callback_data.chat_id
        cmd_id = callback_data.cmd_id
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
            text=text, reply_markup=back_chat_menu_keyboard(chat_id),
            parse_mode="Markdown")

    elif callback_data.action == "chat_cmd_choose":
        chat_id = callback_data.chat_id
        chat = await bot.get_chat(chat_id)
        title = chat.title or f"{chat_id}"
        await chat_menu(call.message.message_id, chat_id, title, storage, call.message, bot)

    elif callback_data.action == "back_to_chat_choose":
        chats = (storage.users_cache.get(str(call.from_user.id)) or {}).get("chats")
        kb = await choose_chat_keyboard(chats, bot) if chats else None
        if kb and kb.inline_keyboard:
            await bot.edit_message_text("*Выберите чат для настройки: *", chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        parse_mode="Markdown",
                                        reply_markup=kb)
        else:
            await bot.edit_message_text("❗ *Вы не являетесь админом ни одного из чатов, где есть бот*",
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id, parse_mode="Markdown")
    await call.answer()
