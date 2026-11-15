from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def response_keyboard(user_name):
    text = f"@{user_name} " if user_name else " "
    kb = [[InlineKeyboardButton(text="Ответить", switch_inline_query_current_chat=text)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура меню команд
def commands_keyboard():
    kb = [[InlineKeyboardButton(text="➕ Создать команду", callback_data="btn_add_command", style="primary")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура просмотра деталей отдельной команды
def command_details_keyboard(cmd_id: str, bot_message):
    kb = [
        [InlineKeyboardButton(text="🗑️ Удалить команду", callback_data=f"btn_delete_command {cmd_id}", style="danger")],
        [InlineKeyboardButton(text="⤴️ Вернуться", callback_data=f"btn_back {bot_message}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура возврата в меню команд
def back_keyboard(bot_message):
    kb = [[InlineKeyboardButton(text="⤴️ Вернуться", callback_data="btn_back" + f" {bot_message}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура подтверждения, что все верно или отклонения
def final_step_keyboard(cmd_id, bot_message_id):
    kb = [[InlineKeyboardButton(text="Все верно!", callback_data="btn_all_right", style="success")],
    [InlineKeyboardButton(text="Отмена", callback_data=f"btn_back {bot_message_id} {cmd_id}",
                                          style="danger")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)
