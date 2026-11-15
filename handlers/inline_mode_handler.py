from aiogram import Router, types, F
from config import EMOJI_TEMPLATE
from database.storage import Storage
from utils.text import clean_md
from keyboards.inline_mode_keyboards import inquery_keyboard, response_keyboard

inline_handler_router = Router()


@inline_handler_router.inline_query()
async def inline_handler(query: types.InlineQuery, storage):
    user_input = clean_md(query.query.strip()).lower()
    user_id = str(query.from_user.id)
    user_first_name = clean_md(query.from_user.first_name)
    user_name = clean_md(query.from_user.username)

    storage.save_user(query.from_user)

    # Убираем повторы пользовательских команд среди топовых команд
    user_commands = storage.commands_cache.get(user_id, [])
    user_cmd_ids = {cmd["id"] for cmd in user_commands}
    all_commands = user_commands + [cmd for cmd in storage.commands_top if cmd["id"] not in user_cmd_ids]

    # Находим юзернейм получателя
    recipient_user_name = ""
    user_input_search = user_input.lower()
    if user_input:
        parts = user_input.split(" ")
        if parts[0][0] == "@":
            recipient_user_name = parts[0][1:]
            user_input_search = " ".join(parts[1:])
        elif parts[-1][0] == "@":
            recipient_user_name = parts[-1][1:]
            user_input_search = " ".join(parts[:-1])

    recipient_first_name = storage.usernames_cache.get(recipient_user_name, recipient_user_name)

    results = []
    for cmd in all_commands:
        emoji = cmd["title"].split()[0] + " | "
        if (not user_input_search or user_input_search in cmd["title"].lower()) and len(results) < 50:
            # Сообщение с запросом на разрешение, нужно дождаться айдишника того кто нажмет
            if recipient_user_name == "" or user_name == recipient_user_name:
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=user_first_name + " " + cmd["text_response"] + " @username",
                        input_message_content=types.InputTextMessageContent(message_text=emoji +
                                                                                         f"[{user_first_name}]({"https://t.me/" + user_name if user_name is not None else "tg://user?id=" + user_id}) " +
                                                                                         cmd["text_inquery"],
                                                                            parse_mode="Markdown",
                                                                            link_preview_options=types.LinkPreviewOptions(
                                                                                is_disabled=True)
                                                                            ),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                        reply_markup=inquery_keyboard(cmd["id"], user_id)
                    )
                )
            # Сообщение без запроса, уже готовое с нужными айдишниками
            else:
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=user_first_name + " " + cmd["text_response"] + f" @{recipient_user_name}",
                        input_message_content=types.InputTextMessageContent(message_text=emoji +
                                                                                         f"[{user_first_name}]({"https://t.me/" + user_name if user_name is not None else "tg://user?id=" + user_id}) " +
                                                                                         cmd[
                                                                                             "text_response"] + f" [{recipient_first_name}](https://t.me/{recipient_user_name})",
                                                                            parse_mode="Markdown",
                                                                            link_preview_options=types.LinkPreviewOptions(
                                                                                is_disabled=True)
                                                                            ),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                        reply_markup=response_keyboard(user_name)
                    )
                )
    await query.answer(results, button=types.InlineQueryResultsButton(text="💚  Создать свою команду",
                                                                      start_parameter="create_command"),
                       cache_time=10, is_personal=True)


@inline_handler_router.chosen_inline_result(F.query.contains("@"))
async def handle_chosen_inline(result: types.ChosenInlineResult, storage: Storage):
    storage.increment_uses(result.result_id)
