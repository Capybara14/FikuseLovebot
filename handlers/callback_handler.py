from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd
from keyboards.chat_mode_keyboards import back_keyboard
from keyboards.inline_mode_keyboards import response_keyboard

callback_handler_router = Router()


# 1. Кнопки из инлайн-сообщений (в любом чате)
@callback_handler_router.callback_query(F.inline_message_id, F.data.startswith("btn_"))
async def inline_buttons_handler(call: types.CallbackQuery, storage):
    await call.answer()
    storage.save_user(call.from_user)
    parts = call.data.split(" ")

    if parts[0] == "btn_accept":
        cmd_id = parts[1]
        author_msg_user_id = parts[2]
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        author_msg_first_name = storage.users_cache[author_msg_user_id].get("user_first_name",
                                                                            None) or author_msg_user_name or author_msg_user_id
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = cmd["title"].split()[0] + " | "
        if str(call.from_user.id) != parts[2]:
            storage.increment_uses(cmd_id)
            text = emoji + f"[{author_msg_first_name}]({"https://t.me/" + author_msg_user_name if author_msg_user_name is not None else "tg://user?id=" + author_msg_user_id}) " + \
                   cmd[
                       "text_response"].lower() + f" [{call.from_user.first_name}]({"https://t.me/" + call.from_user.username if call.from_user.username is not None else "tg://user?id=" + str(call.from_user.id)})"
            await call.bot.edit_message_text(
                text=text,
                inline_message_id=call.inline_message_id,
                reply_markup=response_keyboard(author_msg_user_name),
                parse_mode="Markdown",
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )

    elif parts[0] == "btn_deny":
        cmd_id = parts[1]
        author_msg_user_id = parts[2]
        author_msg_user_name = storage.users_cache[author_msg_user_id].get("user_name", None)
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        emoji = "❌ | "
        if str(call.from_user.id) != parts[2]:
            storage.increment_uses(cmd_id)
            text = emoji + f"[{call.from_user.first_name}]({"https://t.me/" + call.from_user.username if call.from_user.username is not None else "tg://user?id=" + str(call.from_user.id)}) " + \
                   cmd["text_deny"]
            await call.bot.edit_message_text(
                text=text,
                inline_message_id=call.inline_message_id,
                reply_markup=response_keyboard(author_msg_user_name),
                parse_mode="Markdown",
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )


# 2. Кнопки из обычных сообщений в ЛС
@callback_handler_router.callback_query(F.message, F.data.startswith("btn_"))
async def pm_buttons_handler(call: types.CallbackQuery, storage, state: FSMContext):
    await call.answer()
    storage.save_user(call.from_user)
    parts = call.data.split(" ")

    if parts[0] == "btn_add_command":
        if len(storage.commands_cache.get(str(call.from_user.id), [])) < config.LIMIT_OF_COMMANDS:
            await call.bot.edit_message_text(text="*Введите название своей команды*\n\n(_Пример:_ `Поцелуй`)",
                                             inline_message_id=call.inline_message_id,
                                             chat_id=call.message.chat.id, message_id=call.message.message_id,

                                             reply_markup=back_keyboard(call.message.message_id),
                                             parse_mode="Markdown")
            await state.set_state(CreateCmd.title)
        else:
            await call.bot.edit_message_text(text="☹️  *Вы достигли максимального числа команд*",
                                             inline_message_id=call.inline_message_id, chat_id=call.message.chat.id,
                                             reply_markup=back_keyboard(call.message.message_id), parse_mode="Markdown")

    elif parts[0] == "btn_all_right":
        successfully_create(call)

    elif parts[0] == "btn_back":
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        bot_message = call.message.message_id
        if len(parts) > 2:
            cmd_id = parts[2]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = find_cmd(cmd_id)
            if not cmd: return
            commands_cache[author_cmd_id].remove(cmd)
        if len(parts) > 1:
            bot_message = parts[1]
        if commands_cache.get(str(call.from_user.id), None) is None or len(commands_cache[str(call.from_user.id)]) == 0:
            text = "😶  *У вас ещё нет команд, выберите действие*"
        else:
            text = f"*Ваши команды:*\n\n"
            for cmd_id in commands_cache[str(call.from_user.id)]:
                text += f"   — {cmd_id["title"]} ([Детали](https://t.me/{BOT_USERNAME}?start={cmd_id["id"]}_{bot_message}))\n\n"
            text += f" "
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=commands_keyboard(),
            parse_mode="Markdown")

    elif parts[0] == "btn_delete_command":
        try:
            cmd_id = parts[1]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = find_cmd(cmd_id)
            if not cmd: return
            commands_cache[author_cmd_id].remove(cmd)
            text = f"✅ *Команда успешно удалена*"
        except:
            text = "❌ Ошибка удаления команды"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=back_keyboard(call.message.message_id),
            parse_mode="Markdown")

    elif parts[0] == "btn_refresh":
        top_calculator(False, call.from_user.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="*♻️  Команды успешно отсортированы*", reply_markup=back_keyboard(call.message.message_id),
            parse_mode="Markdown")
