from aiogram.filters.callback_data import CallbackData


class BtnCallback(CallbackData, prefix="btn"):
    action: str
    cmd_id: str | None = None
    user_id: str | None = None
    chat_id: str | None = None
    page: int | None = None
    gender: str | None = None
    message_id: str | None = None
