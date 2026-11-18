import asyncio
import html
import time
from aiogram.filters import Command
from aiogram import Router, F, types
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_ADMIN, IS_NOT_MEMBER, MEMBER, RESTRICTED
from aiogram.exceptions import TelegramForbiddenError

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
    msg = await message.reply("*Список админов обновлен*", parse_mode="Markdown")
    await asyncio.sleep(config.SERVICE_MESSAGES_TIMEOUT)
    await msg.delete()
    await message.delete()


@chat_mode_router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def rp_handler(message: types.Message, storage):
    reply = message.reply_to_message
    if not reply:
        return

    word = message.text.split(maxsplit=1)[0].strip().lower()
    cmds = storage.chats_cache.get(str(message.chat.id), {}).get("cmds", {})
    if word not in cmds:
        return

    cmd_id = cmds[word]
    cmd = storage.find_cmd(cmd_id)
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

    if reply.sender_chat:
        target_id = reply.sender_chat.id
        target_username = reply.sender_chat.username
        target_first_name = reply.sender_chat.title
        link_target = html_link_to_user(target_id, target_username, True)
    else:
        target_id = reply.from_user.id
        target_username = reply.from_user.username
        target_first_name = reply.from_user.first_name
        link_target = html_link_to_user(target_id, target_username)

    gender = storage.users_cache.get(author_id, {}).get("gender")
    text = (
        f'{cmd["title"].split()[0]} | '
        f"{link_author}{html.escape(author_first_name)}</a> "
        f"{gender_match_text(cmd['text_response'], gender)} "
        f"{link_target}{html.escape(target_first_name)}</a>"
    )

    await message.answer(
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
