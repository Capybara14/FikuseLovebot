from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

import config
from handlers.create_command import CreateCmd
from keyboards.pm_mode_keyboards import commands_keyboard, command_details_keyboard, back_cmd_menu_keyboard, settings_keyboard

commands_router = Router()


@commands_router.message(Command("start"))
async def start_worker(message: types.Message, storage, bot, state):
    parts = message.text.split()
    if len(parts) == 1:
        await message.reply(
            text=f'👋  *Привет! Это бот для RP команд.*\n\nПросто введи `@{config.BOT_USERNAME}` и выбирай команду!\n\nЕсли что-то не понятно, используй /help',
            parse_mode="Markdown")
    elif parts[1] == "create_command":
        await create_command(message, storage, state, bot)
    else:
        option_parts = parts[1].split("_")
        user_id = option_parts[0]
        cmd_id = user_id + "_" + option_parts[1]
        bot_message = int(option_parts[2])
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        cmd = storage.find_cmd(cmd_id)
        if not cmd: return
        await bot.edit_message_text(text=
                                    f"*👀  Детали команды:*\n\n"
                                    f"   • _Название:_ {cmd['title']}\n"
                                    f"   • _Текст запроса:_ {cmd['text_inquery']}\n"
                                    f"   • _Текст согласия:_ {cmd['text_response']}\n"
                                    f"   • _Текст отказа:_ {cmd['text_deny']}\n"
                                    f"   • _Стикер-превью:_ {"есть" if cmd.get("thumb_url", None) else "отсутствует"}\n\n"
                                    f"_Число использований:_ {cmd['uses_count']}\n",
                                    chat_id=message.chat.id,
                                    message_id=bot_message,
                                    reply_markup=command_details_keyboard(cmd_id, bot_message), parse_mode="Markdown")


# Меню команд
@commands_router.message(Command("my_commands"))
async def my_command_worker(message: types.Message, state: FSMContext, storage):
    target_id = str(message.from_user.id)
    if str(message.from_user.id) in config.ADMINS and len(message.text.split()) == 2:
        target_id = message.text.split()[1]
    bot_message = await message.reply(text="_Загрузка команд..._", parse_mode="Markdown")
    if storage.commands_cache.get(target_id, None) is None or len(
            storage.commands_cache[target_id]) == 0:
        text = "😶  *У вас ещё нет команд, выберите действие*"
    else:
        text = f"*Ваши команды:*\n\n"
        for cmd in storage.commands_cache[target_id]:
            text += f"   — {cmd["title"]} ([Детали](https://t.me/{config.BOT_USERNAME}?start={cmd["id"]}_{bot_message.message_id}))\n\n"
        text += f" "
    await bot_message.edit_text(text=text, parse_mode="Markdown",
                                reply_markup=commands_keyboard())


@commands_router.message(Command("settings"))
async def settings_worker(message, storage, state):
    await message.reply(text=f"*⚙️ Настройки:*", reply_markup=settings_keyboard(str(message.from_user.id), storage),
                        parse_mode="Markdown")


@commands_router.message(Command("help"))
async def help_worker(message):
    await message.reply(
        text="*💚 Инструкция и советы:*\n    • Если в поле ввода ввести юзернейм цели, то подтверждение не потребуется\n    • Если при создании команды использовать скобки с вариантом для женского пола, например: поцеловался(лась) или его(её), то для людей с указанным в настройках полом, сообщение будет меняться в соответствии с ним\n\n*👾 Доступные команды:*\n    /start — Приветствие\n    /new\\_command — создать команду\n    /my\\_commands — просмотр твоих команд",
        parse_mode="Markdown")


@commands_router.message(Command("new_command"))
async def create_command_worker(message, storage, state, bot):
    await create_command(message, storage, state, bot)


async def create_command(message: types.Message, storage, state: FSMContext, bot):
    if len(storage.commands_cache.get(str(message.from_user.id), [])) < config.LIMIT_OF_COMMANDS:
        bot_message = await message.reply(text="_Загрузка..._", parse_mode="Markdown")
        await bot.edit_message_text(text="*Введите название своей команды*\n\n(_Пример:_ `Поцелуй`)",
                                    chat_id=message.chat.id,
                                    message_id=bot_message.message_id,
                                    reply_markup=back_cmd_menu_keyboard(bot_message.message_id),
                                    parse_mode="Markdown")
        await state.set_state(CreateCmd.title)
    else:
        await message.reply(text="☹️  *Вы достигли максимального числа команд*",
                            reply_markup=back_cmd_menu_keyboard(message.message_id), parse_mode="Markdown")


@commands_router.message(Command("ban"))
async def ban_worker(message, storage, state, bot):
    if str(message.from_user.id) in config.ADMINS:
        user_id = message.text.split(" ", 1)[1]
        storage.set_ban(user_id, True)
        await message.reply(
            text=f"*Пользователь {user_id} забанен.*\nОн не сможет использовать бота ни в каком виде, а все его команды удалены.",
            parse_mode="Markdown")


@commands_router.message(Command("unban"))
async def unban_worker(message, storage, state, bot):
    if str(message.from_user.id) in config.ADMINS:
        user_id = message.text.split(" ", 1)[1]
        storage.set_ban(user_id, False)
        await message.reply(text=f"*Пользователь {user_id} разбанен.*", parse_mode="Markdown")
