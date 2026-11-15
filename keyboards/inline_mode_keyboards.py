from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



def inquery_keyboard(cmd_id: str, user_id: str):
    kb = [[InlineKeyboardButton(text ="Принять", callback_data=f"btn_accept {cmd_id} {user_id}",
                                style="success"),
           InlineKeyboardButton(text="Отказаться", callback_data=f"btn_deny {cmd_id} {user_id}",
                                style="danger")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def response_keyboard(user_name):
    text = f"@{user_name} " if user_name else " "
    kb = [[InlineKeyboardButton(text ="Ответить", switch_inline_query_current_chat=text)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

