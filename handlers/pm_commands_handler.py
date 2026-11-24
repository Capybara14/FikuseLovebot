from aiogram import Router, types, F
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd
from keyboards.pm_mode_keyboards import command_details_keyboard, back_cmd_menu_keyboard, \
    choose_chat_keyboard, chat_command_details_keyboard, big_keyboard
from utils.menus import cmd_menu

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
        await create_command(message, storage, state, bot)
    elif parts[1].split("_")[0] == "chatcmd":
        option_parts = parts[1].split("_")[1:]
        cmd_id = option_parts[0] + "_" + option_parts[1]
        chat_id = option_parts[2]
        bot_message_id = int(option_parts[3])
        if chat_id in storage.users_cache[str(message.from_user.id)].get("chats"):
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            cmd = storage.find_cmd(cmd_id)
            if not cmd: return
            await bot.edit_message_text(text=
                                        f"*Детали команды:*\n\n"
                                        f"   • _Название:_ {cmd['title']}\n"
                                        f"   • _Текст согласия:_ {cmd['text_response']}\n"
                                        f"   • _Текст отказа:_ {cmd['text_deny']}\n"
                                        f"   • _Стикер-превью:_ {"есть" if cmd.get("thumb_url", None) else "отсутствует"}\n\n"
                                        f"_Число использований:_ {cmd['uses_count']}\n",
                                        chat_id=message.chat.id,
                                        message_id=bot_message_id,
                                        reply_markup=chat_command_details_keyboard(chat_id, cmd_id, bot_message_id),
                                        parse_mode="Markdown")

    elif parts[1].split("_")[0] == "mycmd":
        option_parts = parts[1].split("_")[1:]
        user_id = option_parts[0]
        cmd_id = user_id + "_" + option_parts[1]
        bot_message = int(option_parts[2])
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        await bot.edit_message_text(text=
                                    f"*Детали команды:*\n\n"
                                    f"   • _Название:_ {cmd['title']}\n"
                                    f"   • _Текст согласия:_ {cmd['text_response']}\n"
                                    f"   • _Текст отказа:_ {cmd['text_deny']}\n"
                                    f"   • _Стикер-превью:_ {"есть" if cmd.get("thumb_url", None) else "отсутствует"}\n\n"
                                    f"_Число использований:_ {cmd['uses_count']}\n",
                                    chat_id=message.chat.id,
                                    message_id=bot_message,
                                    reply_markup=command_details_keyboard(cmd_id, bot_message), parse_mode="Markdown")


# Меню команд
@pm_commands_router.message(F.text == "📋 Мои команды")
@pm_commands_router.message(Command("my_commands"))
async def my_command_worker(message: types.Message, state: FSMContext, storage, bot):
    bot_message = await message.answer(text="_Загрузка..._", parse_mode="Markdown")
    if str(message.from_user.id) in config.ADMINS and len(message.text.split()) == 2:
        target_id = message.text.split()[1]
        await cmd_menu(bot_message.message_id, message, bot, storage, target_id)
        return
    await cmd_menu(bot_message.message_id, message, bot, storage)


@pm_commands_router.message(F.text == "💚 Помощь")
@pm_commands_router.message(Command("help"))
async def help_worker(message):
    await message.answer(
        text="*💚 Помощь и советы:*\n    • Если в поле ввода ввести юзернейм цели, то подтверждение не потребуется\n    • Если при создании команды использовать скобки с вариантом для женского пола, например: поцеловался(лась) или его(её), то для людей с указанным в настройках полом, сообщение будет меняться в соответствии с ним    • Доступ к изменению команд чата имеют все админы чата\n\n*👾 Доступные команды:*\n    /start — Приветствие\n    /new\\_command — создать команду\n    /my\\_commands — просмотр твоих команд\n    /my\\_chats — просмотр и настройка твоих чатов",
        parse_mode="Markdown", reply_markup=big_keyboard())


@pm_commands_router.message(F.text == "➕ Создать команду")
@pm_commands_router.message(Command("new_command"))
async def create_command_worker(message, storage, state, bot):
    await create_command(message, storage, state, bot)


async def create_command(message: types.Message, storage, state: FSMContext, bot):
    if len(storage.commands_cache.get(str(message.from_user.id), [])) < config.LIMIT_OF_COMMANDS:
        bot_message = await message.answer(text="_Загрузка..._", parse_mode="Markdown")
        await bot.edit_message_text(
            text="*Введите название своей команды*\n\n\\[Твой ник] хочет *ТЕКСТ*\n\n(_Этот текст будет отображаться после слова «хочет» и использоваться как триггер в чатах. Пример:_ `Поцеловать`)",
            chat_id=message.chat.id,
            message_id=bot_message.message_id,
            reply_markup=back_cmd_menu_keyboard(bot_message.message_id),
            parse_mode="Markdown")
        await state.set_state(CreateCmd.title)
    else:
        await message.answer(text="❗ *Вы достигли максимального числа команд*",
                             reply_markup=back_cmd_menu_keyboard(message.message_id), parse_mode="Markdown")


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
    chats = storage.users_cache[str(message.from_user.id)].get("chats")
    bot_message = await message.answer("_Загрузка..._", parse_mode="Markdown")
    if chats is not None and len(chats) > 0:
        await bot.edit_message_text("*Выберите чат для настройки:* ", chat_id=message.chat.id,
                                    message_id=bot_message.message_id,
                                    parse_mode="Markdown",
                                    reply_markup=await choose_chat_keyboard(chats, bot_message.message_id, bot,
                                                                            storage))
    else:
        await bot.edit_message_text("❗ *Вы не являетесь админом ни одного из чатов, где есть бот*",
                                    chat_id=message.chat.id,
                                    message_id=bot_message.message_id, parse_mode="Markdown")
