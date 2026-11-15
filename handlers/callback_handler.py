from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

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
    pass
