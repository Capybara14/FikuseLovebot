from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.callbacks import BtnCallback


def inquery_keyboard(cmd_id: str, user_id: str):
    kb = [[
        InlineKeyboardButton(
            text="Принять",
            callback_data=BtnCallback(action="accept", cmd_id=cmd_id, user_id=str(user_id)).pack(),
            style="success",
        ),
        InlineKeyboardButton(
            text="Отказаться",
            callback_data=BtnCallback(action="deny", cmd_id=cmd_id, user_id=str(user_id)).pack(),
            style="danger",
        ),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def response_keyboard(user_name):
    text = f"@{user_name} " if user_name else " "
    kb = [[InlineKeyboardButton(text ="Ответить", switch_inline_query_current_chat=text, style="primary")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

