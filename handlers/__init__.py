from aiogram import Router
from . import inline_handler, callback_handler

handler_router = Router()
handler_router.include_router(inline_handler.inline_handler_router)
handler_router.include_router(callback_handler.callback_handler_router)