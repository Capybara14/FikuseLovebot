import asyncio
from contextlib import suppress
import html
import time
from aiogram.filters import Command
from aiogram import Router, F, types
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_ADMIN, IS_NOT_MEMBER, MEMBER, RESTRICTED
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import config
from keyboards.inline_mode_keyboards import response_keyboard
from utils.gender import gender_match_text
from utils.text import html_link_to_user

chat_mode_router = Router()
chat_mode_router.message.filter(F.chat.type.in_({"group", "supergroup"}))
chat_mode_router.my_chat_member.filter(F.chat.type.in_({"group", "supergroup"}))
NOT_ADMIN = MEMBER | RESTRICTED | IS_NOT_MEMBER


# 1. Бота добавили сразу с админкой ИЛИ повысили до админа позже
@chat_mode_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=NOT_ADMIN >> IS_ADMIN)
)
async def bot_added_as_admin(event: ChatMemberUpdated, storage, bot):
    admins = await bot.get_chat_administrators(event.chat.id)
    await update_admins(admins, str(event.chat.id), bot, storage)

    try:
        msg = await event.answer(
            "💚 *Бот готов к работе!*\n"
            "Настроить команды для этого чата могут админы в личных сообщениях", parse_mode="Markdown"
        )
        await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
        await msg.delete()
    except TelegramForbiddenError:
        pass


# 2. Бота добавили как обычного участника (без прав администратора)
@chat_mode_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> (MEMBER | RESTRICTED))
)
async def bot_added_without_admin(event: ChatMemberUpdated):
    try:
        msg = await event.answer(
            "❗ *Для работы мне нужны права администратора.*\n", parse_mode="Markdown"
        )
        await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
        await msg.delete()
    except TelegramForbiddenError:
        pass


# 3. Сняли с бота админку
@chat_mode_router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=IS_ADMIN >> NOT_ADMIN)
)
async def bot_demoted(event: ChatMemberUpdated):
    try:
        msg = await event.answer(
            "❗ *Для работы мне нужны права администратора.*\n", parse_mode="Markdown"
        )
        await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
        await msg.delete()
    except TelegramForbiddenError:
        pass


@chat_mode_router.chat_member(ChatMemberUpdatedFilter(IS_ADMIN >> NOT_ADMIN))
@chat_mode_router.chat_member(ChatMemberUpdatedFilter(NOT_ADMIN >> IS_ADMIN))
async def admins_change(event: types.ChatMemberUpdated, bot, storage):
    admins = await bot.get_chat_administrators(event.chat.id)
    await update_admins(admins, str(event.chat.id), bot, storage)


@chat_mode_router.message(Command("refresh"))
async def refresh_worker(message, storage, bot):
    now = time.monotonic()
    if now - float(storage.chats_cache[str(message.chat.id)].get("refresh_cd", 0)) < config.SERVICE_MESSAGES_TIMEOUT:
        return
    storage.chats_cache[str(message.chat.id)]["refresh_cd"] = now

    admins = await bot.get_chat_administrators(message.chat.id)
    await update_admins(admins, str(message.chat.id), bot, storage)
    msg = await message.answer("*Список админов обновлен*", parse_mode="Markdown")
    await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
    with suppress(TelegramBadRequest):
        await msg.delete()
    with suppress(TelegramBadRequest):
        await message.delete()


@chat_mode_router.message(Command("chat_commands"))
async def help_worker(message, storage):
    if storage.chats_cache[str(message.chat.id)]["cmds"] == {}:
        text = "❗ В этом чате ещё нет команд, добавленных админами"
    else:
        text = f"*📋 Команды чата:*\n\n"
        for i in storage.chats_cache[str(message.chat.id)]["cmds"]:
            text+=f"   — {i}\n\n"

    bot_message = await message.answer(
        text=text,
        parse_mode="Markdown")
    await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
    with suppress(TelegramBadRequest):
        await bot_message.delete()
    with suppress(TelegramBadRequest):
        await message.delete()


def _migrate_chat(old_chat_id: str, new_chat_id: str, storage) -> None:
    old_data = storage.chats_cache.pop(old_chat_id, None)
    if not old_data:
        return

    new_data = storage.chats_cache.get(new_chat_id)
    if new_data is None:
        storage.chats_cache[new_chat_id] = old_data
    else:
        merged_cmds = dict(old_data.get("cmds", {}))
        merged_cmds.update(new_data.get("cmds", {}))
        new_data["cmds"] = merged_cmds
        if not new_data.get("admins") and old_data.get("admins"):
            new_data["admins"] = old_data["admins"]

    for admin_id in old_data.get("admins", []):
        user_chats = (storage.users_cache.get(admin_id) or {}).get("chats")
        if user_chats and old_chat_id in user_chats:
            if new_chat_id in user_chats:
                user_chats.remove(old_chat_id)
            else:
                user_chats[user_chats.index(old_chat_id)] = new_chat_id


@chat_mode_router.message(F.migrate_to_chat_id)
async def chat_migrated_to(message: types.Message, storage):
    _migrate_chat(str(message.chat.id), str(message.migrate_to_chat_id), storage)


@chat_mode_router.message(F.migrate_from_chat_id)
async def chat_migrated_from(message: types.Message, storage):
    _migrate_chat(str(message.migrate_from_chat_id), str(message.chat.id), storage)


def _find_command(text: str, cmds: dict[str, str]) -> tuple[str, str] | None:
    lower_text = text.lower()
    cmd_id = cmds.get(lower_text)
    if cmd_id is not None:
        return cmd_id, ""

    parts = lower_text.split(maxsplit=1)
    if len(parts) < 2:
        return None

    cmd_id = cmds.get(parts[0])
    if cmd_id is not None:
        return cmd_id, text.split(maxsplit=1)[1]

    for trigger, cmd_id in cmds.items():
        if lower_text.startswith(trigger) and lower_text[len(trigger)].isspace():
            return cmd_id, text[len(trigger):].lstrip()
    return None


@chat_mode_router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def rp_handler(message: types.Message, storage):
    cmds = storage.chats_cache.get(str(message.chat.id), {}).get("cmds")
    if not cmds:
        return
    matched = _find_command(message.text, cmds)
    if not matched:
        return

    cmd_id, remainder = matched
    cmd = storage.find_cmd(cmd_id)
    if not cmd:
        return

    target = None
    reply_target = message
    if remainder.startswith("@"):
        token = remainder.split(maxsplit=1)[0]
        if len(token) > 1:
            username = token[1:]
            username_lower = username.lower()
            target = (
                html_link_to_user(None, username_lower),
                storage.usernames_cache.get(username_lower) or username,
            )
    elif remainder and message.entities:
        for entity in message.entities:
            if entity.type == "text_mention" and entity.user and remainder.startswith(
                    entity.extract_from(message.text)):
                target = (
                    html_link_to_user(entity.user.id, entity.user.username),
                    entity.user.first_name,
                )
                break

    if not target:
        reply = message.reply_to_message
        if not reply:
            return
        reply_target = reply
        if reply.sender_chat:
            target = (
                html_link_to_user(reply.sender_chat.id, reply.sender_chat.username, True),
                reply.sender_chat.title,
            )
        else:
            target = (
                html_link_to_user(reply.from_user.id, reply.from_user.username),
                reply.from_user.first_name,
            )

    link_target, target_first_name = target

    storage.increment_uses(cmd_id)

    if message.sender_chat:
        author_id = message.sender_chat.id
        author_username = message.sender_chat.username
        author_first_name = message.sender_chat.title
        link_author = html_link_to_user(author_id, author_username, True)
    else:
        author_id = message.from_user.id
        author_username = message.from_user.username
        author_first_name = message.from_user.first_name
        link_author = html_link_to_user(author_id, author_username)

    gender = storage.users_cache.get(str(author_id), {}).get("gender")
    text = (
        f'{cmd["title"].split()[0]} | '
        f"{link_author}{html.escape(author_first_name)}</a> "
        f"{gender_match_text(cmd['text_response'], gender)} "
        f"{link_target}{html.escape(target_first_name)}</a>"
    )

    await reply_target.reply(
        text=text,
        reply_markup=response_keyboard(author_username),
        parse_mode="HTML",
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )


async def update_admins(admins: list, chat_id: str, bot, storage):
    chat_data = storage.chats_cache.setdefault(chat_id, {"admins": [], "cmds": {}})
    old_admins = set(chat_data.get("admins", []))
    admin_ids = [str(admin.user.id) for admin in admins if not admin.user.is_bot]
    chat_data["admins"] = admin_ids

    for i in old_admins - set(admin_ids):
        user_chats = (storage.users_cache.get(i) or {}).get("chats")
        if user_chats and chat_id in user_chats:
            user_chats.remove(chat_id)

    for i in admin_ids:
        if storage.users_cache.get(i):
            if storage.users_cache[i].get("chats") is None:
                storage.users_cache[i]["chats"] = [chat_id]
            elif len(storage.users_cache[i]["chats"]) >= config.LIMIT_OF_COMMANDS:
                continue
            elif chat_id not in storage.users_cache[i]["chats"]:
                storage.users_cache[i]["chats"].append(chat_id)
