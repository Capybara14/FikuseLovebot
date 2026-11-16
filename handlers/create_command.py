import asyncio
from asyncio import create_task

from aiogram import F, types, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.sticker import process_and_upload_sticker
from keyboards.chat_mode_keyboards import final_step_keyboard, back_cmd_menu_keyboard
from utils.text import clean_md

create_command_router = Router()


class CreateCmd(StatesGroup):
    title = State()
    emoji = State()
    thumb_url = State()
    inquery = State()
    response = State()
    deny = State()


@create_command_router.message(CreateCmd.title, F.text)
async def enter_the_name(message: types.Message, state: FSMContext):
    await state.update_data(title=clean_md(message.text).capitalize())
    await message.reply(
        text="*Введите эмодзи для команды*\n\n(_Будет располагаться рядом с названием_)",
        parse_mode="Markdown"
    )
    await state.set_state(CreateCmd.emoji)


@create_command_router.message(CreateCmd.emoji, F.text)
async def enter_the_emoji(message: types.Message, state: FSMContext):
    await state.update_data(title=clean_md(message.text) + " " + await state.get_value("title"))
    await message.reply(text="*Отправьте стикер для иконки команды*\n\n(_Напишите /skip для пропуска_)",
                        parse_mode="Markdown")
    await state.set_state(CreateCmd.thumb_url)


@create_command_router.message(CreateCmd.thumb_url, Command("skip"))
async def skip_sticker(message: types.Message, state: FSMContext):
    await state.update_data(thumb_url=None)
    await message.reply(
        text="*Введите текст запроса на действие*\n\n\\[Твой ник]  *ТЕКСТ*\n\n(_Пример: _`хочет поцеловать`)",
        parse_mode="Markdown")
    await state.set_state(CreateCmd.inquery)


@create_command_router.message(CreateCmd.thumb_url, F.sticker)
async def enter_the_sticker(message: types.Message, bot: Bot, state: FSMContext):
    thumb_url = None
    sticker = message.sticker

    if sticker.is_animated or sticker.is_video:
        file_id = sticker.thumbnail.file_id if sticker.thumbnail else None
    else:
        file_id = sticker.file_id

    if file_id:
        try:
            file_info = await bot.get_file(file_id)
            raw = await bot.download_file(file_info.file_path)
            thumb_url = await asyncio.to_thread(process_and_upload_sticker, raw)
        except Exception as e:
            print(e)

    await state.update_data(thumb_url=thumb_url)
    await message.reply(
        text="*Введите текст запроса на действие*\n\n\\[Твой ник]  *ТЕКСТ*\n\n(_Пример: _`хочет поцеловать`)",
        parse_mode="Markdown"
    )
    await state.set_state(CreateCmd.inquery)


@create_command_router.message(CreateCmd.inquery, F.text)
async def enter_text_inquery(message, state):
    await state.update_data(inquery=clean_md(message.text).lower())
    await message.reply(
        text="*Введите текст совершённого действия*\n\n\\[Твой ник]  *ТЕКСТ*  \\[Ник того, кто принял]\n\n(_Пример: _`поцеловал(а)`)",
        parse_mode="Markdown"
    )
    await state.set_state(CreateCmd.response)


@create_command_router.message(CreateCmd.response, F.text)
async def enter_text_response(message, state):
    await state.update_data(response=clean_md(message.text).lower())
    await message.reply(
        "*Введите текст отказа от действия*\n\n\\[Ник того, кто отказался]  *ТЕКСТ*\n\n(_Пример: _`не хочет целоваться`)",
        parse_mode="Markdown"
    )
    await state.set_state(CreateCmd.deny)


@create_command_router.message(CreateCmd.deny, F.text)
async def final_check(message, state, bot, storage):
    await state.update_data(deny=clean_md(message.text).lower())

    user_id = str(message.from_user.id)
    data = await state.get_data()
    new_command = {
        "title": data["title"],
        "thumb_url": data["thumb_url"],
        "text_inquery": data["inquery"],
        "text_response": data["response"],
        "text_deny": data["deny"],
        "uses_count": "0"
    }

    if user_id not in storage.commands_cache or storage.commands_cache[user_id] == []:
        storage.commands_cache[user_id] = []
        commands_max_num = 0
    else:
        commands_max_num = max([int(i["id"].split("_")[1]) for i in storage.commands_cache[user_id]]) + 1
    storage.commands_cache[user_id].append(new_command | {"id": f"{user_id}_{commands_max_num}"})

    bot_message = await message.reply(text="_Сохранение данных..._", parse_mode="Markdown")
    await bot.edit_message_text(
        text=f"*Проверьте правильность ввода:*\n\n"
             f"   • _Название:_ {new_command['title']}\n"
             f"   • _Запрос:_ {new_command['text_inquery']}\n"
             f"   • _Согласие:_ {new_command['text_response']}\n"
             f"   • _Отказ:_ {new_command['text_deny']}\n"
             f"   • _Стикер-превью:_ {"есть" if new_command.get("thumb_url", None) else "отсутствует"}",
        chat_id=bot_message.chat.id,
        message_id=bot_message.message_id,
        reply_markup=final_step_keyboard(f"{user_id}_{commands_max_num}", bot_message.message_id),
        parse_mode="Markdown"
    )
    await state.clear()


# Завершение
async def successfully_create(call, bot):
    await bot.edit_message_text(
        text="*Команда успешно сохранена!*",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_cmd_menu_keyboard(call.message.message_id),
        parse_mode="Markdown"
    )
