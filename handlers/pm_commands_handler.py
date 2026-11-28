from aiogram import Router, types, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd
from keyboards.pm_mode_keyboards import back_cmd_menu_keyboard, \
    big_keyboard, cancel_cmd_create_keyboard
from utils.menus import cmd_menu, choose_chat_menu

pm_commands_router = Router()
pm_commands_router.message.filter(F.chat.type == ChatType.PRIVATE)


@pm_commands_router.message(Command("start"))
async def start_worker(message: types.Message, storage, bot, state):
    parts = message.text.split()

    if len(parts) == 1:
        await message.answer(
            text=f'👋 *Привет! Это бот для RP команд.*\n\nПросто введи `@{config.BOT_USERNAME}` и выбирай команду!\n\nЕсли что-то не понятно, используй /help',
            parse_mode="Markdown", reply_markup=big_keyboard())
    elif parts[1] == "create_command":
        await create_command(message, storage, state)


# Меню команд
@pm_commands_router.message(F.text == "📋 Мои команды")
@pm_commands_router.message(Command("my_commands"))
async def my_command_worker(message: types.Message, state: FSMContext, storage, bot):
    if str(message.from_user.id) in config.ADMINS and len(message.text.split()) == 2:
        target_id = message.text.split()[1]
        await cmd_menu(message, bot, storage, target_id)
        return
    await cmd_menu(message, bot, storage)


@pm_commands_router.message(F.text == "💚 Помощь")
@pm_commands_router.message(Command("help"))
async def help_worker(message):
    await message.answer(
        text="*💚 Помощь и советы:*\n    • Если в поле ввода ввести юзернейм цели, то подтверждение не потребуется\n    • Если при создании команды использовать скобки с вариантом для женского пола, например: поцеловался(лась) или его(её), то для людей с указанным в настройках полом, сообщение будет меняться в соответствии с ним\n    • Доступ к изменению команд чата имеют все админы чата\n\n*👾 Доступные команды:*\n    /start — Приветствие\n    /new\\_command — создать команду\n    /my\\_commands — просмотр твоих команд\n    /my\\_chats — просмотр и настройка твоих чатов",
        parse_mode="Markdown", reply_markup=big_keyboard())


@pm_commands_router.message(F.text == "➕ Создать команду")
@pm_commands_router.message(Command("new_command"))
async def create_command_worker(message, storage, state):
    await create_command(message, storage, state)


async def create_command(message: types.Message, storage, state: FSMContext):
    if len(storage.commands_cache.get(str(message.from_user.id), [])) < config.LIMIT_OF_COMMANDS:
        await message.answer(
            text="*Введите название своей команды*\n\n\\[Твой ник] хочет *ТЕКСТ*\n\n(_Этот текст будет использоваться как триггер в чатах. Пример:_ `Поцеловать`)",
            reply_markup=cancel_cmd_create_keyboard(),
            parse_mode="Markdown")
        await state.set_state(CreateCmd.title)
    else:
        await message.answer(text="❗ *Вы достигли максимального числа команд*",
                             reply_markup=back_cmd_menu_keyboard(), parse_mode="Markdown")


@pm_commands_router.message(Command("ban"))
async def ban_worker(message, storage):
    if str(message.from_user.id) in config.ADMINS:
        user_id = message.text.split(" ", 1)[1]
        storage.set_ban(user_id, True)
        await message.answer(
            text=f"*Пользователь {user_id} забанен*\nОн не сможет использовать бота ни в каком виде, а все его команды удалены.",
            parse_mode="Markdown", reply_markup=big_keyboard())


@pm_commands_router.message(Command("unban"))
async def unban_worker(message, storage):
    if str(message.from_user.id) in config.ADMINS:
        user_id = message.text.split(" ", 1)[1]
        storage.set_ban(user_id, False)
        await message.answer(text=f"*Пользователь {user_id} разбанен*", parse_mode="Markdown", reply_markup=big_keyboard())


@pm_commands_router.message(F.text == "💬 Мои чаты")
@pm_commands_router.message(Command("my_chats"))
async def my_chats_worker(message, storage, bot):
    await choose_chat_menu(message, bot, storage, message.from_user.id)
