from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import config


# Клавиатура меню команд
def commands_keyboard(user_id: str, storage):
    gender = storage.users_cache.get(user_id).get("gender")
    kb = [
        [InlineKeyboardButton(text="➕ Создать команду", callback_data="btn_add_command", style="primary")],
        [InlineKeyboardButton(text=f"Твой пол: {gender if gender else "Нажимай!"}",
                              callback_data=f"btn_gender {gender}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура просмотра деталей отдельной команды
def command_details_keyboard(cmd_id: str, bot_message_id):
    kb = [
        [InlineKeyboardButton(text="🗑️ Удалить команду", callback_data=f"btn_delete_command {cmd_id}", style="danger")],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=f"btn_back_cmd_menu {bot_message_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура возврата в меню команд
def back_cmd_menu_keyboard(bot_message_id):
    kb = [[InlineKeyboardButton(text="⤴️ Вернуться", callback_data="btn_back_cmd_menu" + f" {bot_message_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура подтверждения, что все верно или отклонения
def final_step_keyboard(cmd_id, bot_message_id):
    kb = [[InlineKeyboardButton(text="Все верно!", callback_data="btn_all_right", style="success")],
          [InlineKeyboardButton(text="Отмена", callback_data=f"btn_back_cmd_menu {bot_message_id} {cmd_id}",
                                style="danger")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def choose_chat_keyboard(chats: set, bot_message_id, bot, storage):
    kb = []
    for chat_id in chats:
        try:
            if len(chats) < config.LIMIT_OF_COMMANDS:
                chat = await bot.get_chat(chat_id)
                title = chat.title or f"Чат {chat_id}"
                kb.append(
                    [InlineKeyboardButton(text=f"{title}",
                                          callback_data=f"btn_chat_cmd_choose {chat_id} {bot_message_id}")])
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
    return InlineKeyboardMarkup(inline_keyboard=kb)


def chat_command_details_keyboard(chat_id, cmd_id, bot_message_id):
    kb = [
        [InlineKeyboardButton(text="🗑️ Удалить команду", callback_data=f"btn_delete_chat_command {chat_id} {cmd_id}",
                              style="danger")],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=f"btn_chat_cmd_choose {chat_id} {bot_message_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def chat_commands_keyboard(bot_message_id, chat_id):
    text = f"@add_cmd:{chat_id}:{bot_message_id}"
    kb = [
        [InlineKeyboardButton(text="➕ Добавить команду", switch_inline_query_current_chat=text, style="primary")],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=f"btn_back_to_chat_choose {bot_message_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def back_chat_menu_keyboard(bot_message_id, chat_id):
    kb = [[InlineKeyboardButton(text="⤴️ Вернуться", callback_data=f"btn_chat_cmd_choose {chat_id} {bot_message_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def big_keyboard():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать команду", style="primary"),
             KeyboardButton(text="📋 Мои команды", style="primary")],
            [KeyboardButton(text="💬 Мои чаты", style="primary"),
             KeyboardButton(text="💚 Помощь", style="primary")],
        ],
        resize_keyboard=True,
    )
    return kb
