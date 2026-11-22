import html

from aiogram import Router, types, F

import config
from config import EMOJI_TEMPLATE
from database.storage import Storage
from utils.gender import gender_match_text
from keyboards.inline_mode_keyboards import inquery_keyboard, response_keyboard
from utils.menus import chat_menu
from utils.text import html_link_to_user

inline_handler_router = Router()


@inline_handler_router.inline_query()
async def inline_handler(query: types.InlineQuery, storage):
    user_input = query.query.strip().lower()
    user_id = str(query.from_user.id)
    user_first_name = query.from_user.first_name
    user_name = query.from_user.username.lower()
    user_gender = storage.users_cache.get(user_id).get("gender")

    # Убираем повторы пользовательских команд среди топовых команд
    user_commands = storage.commands_cache.get(user_id, [])
    user_cmd_ids = {cmd["id"] for cmd in user_commands}
    all_commands = user_commands + [cmd for cmd in storage.commands_top if cmd["id"] not in user_cmd_ids]

    # Находим юзернейм получателя
    recipient_user_name = ""
    user_input_search = user_input.lower()
    parts = user_input.split(" ")
    if user_input:
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
            if "add_cmd" in recipient_user_name and recipient_user_name.split(":")[1] in storage.users_cache.get(
                    user_id).get("chats"):
                add_cmd_parts = recipient_user_name.split(":")
                chat_id = add_cmd_parts[1]
                bot_message_id = add_cmd_parts[2]
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description="Добавить команду " + cmd["title"],
                        input_message_content=types.InputTextMessageContent(message_text=(
                            f"add_cmd {chat_id} {cmd["id"]} {bot_message_id}"
                        ),
                            parse_mode="HTML",
                            link_preview_options=types.LinkPreviewOptions(
                                is_disabled=True)
                        ),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                    )
                )
            elif "info" == recipient_user_name and user_id in config.ADMINS:
                author_id = cmd["id"].split("_")[0]
                author_username = storage.users_cache[author_id]["user_name"]
                author_firstname = storage.users_cache[author_id]["user_first_name"]
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=user_first_name + " " + gender_match_text(cmd["text_response"],
                                                                              user_gender) + " @username",
                        input_message_content=types.InputTextMessageContent(message_text=(
                            f'Команда: {cmd["id"]}\n'
                            f'Автор: {html_link_to_user(author_id, author_username)}'
                            f"{html.escape(author_firstname)}</a>\n"
                            f"Имя автора: <code>{author_firstname}</code>\n"
                            f"Айди автора: <code>{author_id}</code>\n"
                            f"Юзернейм автора: <code>@{author_username}</code>\n"),
                            parse_mode="HTML",
                            link_preview_options=types.LinkPreviewOptions(
                                is_disabled=True)
                        ),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                        reply_markup=response_keyboard("info")
                    )
                )
            # Сообщение с запросом на разрешение, нужно дождаться айдишника того кто нажмет
            elif recipient_user_name == "" or user_name == recipient_user_name:
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=user_first_name + " " + gender_match_text(cmd["text_response"],
                                                                              user_gender) + " @username",
                        input_message_content=types.InputTextMessageContent(message_text=(
                            f'{emoji}{html_link_to_user(user_id, user_name)}'
                            f"{html.escape(user_first_name)}</a> "
                            f"хочет {html.escape(cmd['title'].split(maxsplit=1)[-1].lower())}"),
                            parse_mode="HTML",
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
                        id=f"direct:{cmd['id']}",
                        title=cmd["title"],
                        description=user_first_name + " " + gender_match_text(cmd["text_response"],
                                                                              user_gender) + f" @{recipient_user_name}",
                        input_message_content=types.InputTextMessageContent(message_text=(
                            f'{emoji}{html_link_to_user(user_id, user_name)}'
                            f"{html.escape(user_first_name)}</a> "
                            f"{gender_match_text(cmd['text_response'], user_gender)} "
                            f'{html_link_to_user(None, recipient_user_name)}{html.escape(recipient_first_name)}</a>'
                        ),
                            parse_mode="HTML",
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


@inline_handler_router.chosen_inline_result(F.result_id.startswith("direct:"))
async def handle_chosen_inline(result: types.ChosenInlineResult, storage: Storage, state):
    storage.increment_uses(result.result_id.removeprefix("direct:"))


@inline_handler_router.message(F.via_bot, F.text.startswith("add_cmd "))
async def add_cmd_from_inline(message: types.Message, storage, bot):
    if message.via_bot.id != bot.id:
        return
    _, chat_id, cmd_id, bot_message_id = message.text.split(" ")
    cmd_ids = storage.chats_cache[chat_id]["cmds"].values()
    cmds = storage.chats_cache[chat_id]["cmds"]
    if len(cmd_ids) < config.LIMIT_OF_COMMANDS:
        if cmd_id in cmd_ids:
            return
        cmds[storage.find_cmd(cmd_id)["title"][2:].lower().strip()] = cmd_id
        chat = await bot.get_chat(chat_id)
        title = chat.title or f"{chat_id}"
        await chat_menu(bot_message_id, chat_id, title, storage, message, bot)
        await message.delete()
    else:
        await bot.send_message(chat_id=message.from_user.id, text="❗ Вы достигли лимита команд")
