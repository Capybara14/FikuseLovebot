from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import config
from keyboards.callbacks import BtnCallback


# Клавиатура меню команд
def commands_keyboard(user_id: str, storage, page: int = 0):
    gender = (storage.users_cache.get(user_id) or {}).get("gender")
    cmds = storage.commands_cache.get(user_id) or []
    per_page = config.COMMANDS_PER_PAGE
    total_pages = max(1, (len(cmds) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))

    kb = []
    if total_pages > 1:
        prev_btn = (
            InlineKeyboardButton(
                text="⬅️",
                callback_data=BtnCallback(action="cmd_page", user_id=str(user_id), page=page - 1).pack(),
                style="primary",
            )
            if page > 0
            else InlineKeyboardButton(text="\u200b", callback_data=BtnCallback(action="noop").pack())
        )
        counter_btn = InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data=BtnCallback(action="noop").pack(),
            style="primary",
        )
        next_btn = (
            InlineKeyboardButton(
                text="➡️",
                callback_data=BtnCallback(action="cmd_page", user_id=str(user_id), page=page + 1).pack(),
                style="primary",
            )
            if page < total_pages - 1
            else InlineKeyboardButton(text="\u200b", callback_data=BtnCallback(action="noop").pack())
        )
        kb.append([prev_btn, counter_btn, next_btn])
    kb.append([
        InlineKeyboardButton(
            text=f"Твой пол: {gender if gender else 'Нажимай!'}",
            callback_data=BtnCallback(action="gender", gender=gender, page=page).pack(),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура просмотра деталей отдельной команды
def command_details_keyboard(cmd_id: str):
    kb = [
        [InlineKeyboardButton(
            text="🗑️ Удалить команду",
            callback_data=BtnCallback(action="delete_command", cmd_id=cmd_id).pack(),
            style="danger",
        )],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=BtnCallback(action="back_cmd_menu").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура возврата в меню команд
def back_cmd_menu_keyboard():
    kb = [[InlineKeyboardButton(text="⤴️ Вернуться", callback_data=BtnCallback(action="back_cmd_menu").pack())]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def delete_message_keyboard(message):
    kb = [[InlineKeyboardButton(text="⤴️ Вернуться",
                                callback_data=BtnCallback(action="delete_msg", message_id=str(message.message_id)).pack())]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура подтверждения, что все верно или отклонения
def final_step_keyboard(cmd_id):
    kb = [
        [InlineKeyboardButton(text="Все верно!", callback_data=BtnCallback(action="all_right").pack(),
                              style="success")],
        [InlineKeyboardButton(
            text="Отмена",
            callback_data=BtnCallback(action="back_cmd_menu", cmd_id=cmd_id).pack(),
            style="danger",
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def choose_chat_keyboard(chats: set, bot):
    kb = []
    for chat_id in chats:
        try:
            if len(chats) < config.LIMIT_OF_COMMANDS:
                chat = await bot.get_chat(chat_id)
                title = chat.title or f"Чат {chat_id}"
                kb.append([
                    InlineKeyboardButton(
                        text=f"{title}",
                        callback_data=BtnCallback(action="chat_cmd_choose", chat_id=str(chat_id)).pack(),
                    )
                ])
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
    return InlineKeyboardMarkup(inline_keyboard=kb)


def chat_command_details_keyboard(chat_id, cmd_id):
    kb = [
        [InlineKeyboardButton(
            text="🗑️ Удалить команду",
            callback_data=BtnCallback(action="delete_chat_command", chat_id=str(chat_id), cmd_id=cmd_id).pack(),
            style="danger",
        )],
        [InlineKeyboardButton(
            text="⤴️ Вернуться",
            callback_data=BtnCallback(action="chat_cmd_choose", chat_id=str(chat_id)).pack(),
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def chat_commands_keyboard(bot_message_id, chat_id):
    text = f"@add_cmd:{chat_id}:{bot_message_id}"
    kb = [
        [InlineKeyboardButton(text="➕ Добавить команду", switch_inline_query_current_chat=text, style="primary")],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=BtnCallback(action="back_to_chat_choose").pack())],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def back_chat_menu_keyboard(chat_id):
    kb = [[
        InlineKeyboardButton(
            text="⤴️ Вернуться",
            callback_data=BtnCallback(action="chat_cmd_choose", chat_id=str(chat_id)).pack(),
        )
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def big_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Мои команды", style="primary"),
             KeyboardButton(text="💬 Мои чаты", style="primary")],
        ],
        is_persistent=True,
        resize_keyboard=True,
    )
    return kb
