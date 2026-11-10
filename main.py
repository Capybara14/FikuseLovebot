import json, os, threading, signal, time, heapq, sys, base64

import requests
import io
from PIL import Image
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
EMOJI_TEMPLATE = "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64/{code}.png"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
IMGBB_KEY = os.getenv("IMGBB_KEY")
FILE_COMMANDS_PATH = "commands.json"
FILE_USERS_PATH = "users.json"
LOCK = threading.Lock()
TIMEOUT = 600

# region НАЧАЛЬНЫЕ НАСТРОЙКИ

# Загружаем из файла в оперативку

commands_cache = {}
users_cache = {}
if os.path.exists(FILE_COMMANDS_PATH):
    with open(FILE_COMMANDS_PATH, "r", encoding="utf-8") as f:
        commands_cache = json.load(f)
if os.path.exists(FILE_USERS_PATH):
    with open(FILE_USERS_PATH, "r", encoding="utf-8") as f:
        users_cache = json.load(f)

# Нужна ли перезапись бд
is_dirty = False

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

while True:
    try:
        bot.set_my_commands([
            types.BotCommand("start", "Главное меню"),
            types.BotCommand("my_commands", "Управление командами"),
            types.BotCommand("instruction", "Инструкция")
        ])
        break
    except:
        time.sleep(TIMEOUT)


# endregion

# Старт и детали указанной команды
@bot.message_handler(commands=['start'])
def start_worker(message):
    save_user(message.from_user.username, message.from_user.first_name)
    parts = message.text.split()

    if len(parts) == 1:
        bot.reply_to(message,
                     f'👋  *Привет! Это бот для RP команд.*\n\nПросто напиши `@{BOT_USERNAME}` и выбирай команду!',
                     parse_mode="Markdown")
    elif parts[1] == "instruction":
        bot.reply_to(message,
                     "*📋  Инструкция:*\n\n   • При использовании можно указать юзернейм цели, тогда подтверждение не потребуется\n   • Для просмотра, создания и удаления собственных команд, используй /my\\_commands\n   • В списке доступных тебе команд всегда отображаются сначала твои, потом общие, отсортированные по частоте использования\n   • Рейтинг самых используемых команд среди всех обновляется раз в 10 минут, а самых используемых среди твоих — после использования /refresh (аналогичная функция есть в меню команд)",
                     parse_mode="Markdown")
    else:
        option_parts = parts[1].split("_")
        user_id = option_parts[0]
        cmd_id = user_id + "_" + option_parts[1]
        bot_message = option_parts[2]
        bot.delete_message(message.chat.id, message.message_id)
        cmd = find_cmd(cmd_id)
        bot.edit_message_text(
            f"*👀  Детали команды:*\n\n"
            f"   • _Название:_ {cmd['title']}\n"
            f"   • _Описание:_ {cmd['desc']}\n"
            f"   • _Текст запроса:_ {cmd['text_inquery']}\n"
            f"   • _Текст согласия:_ {cmd['text_response']}\n"
            f"   • _Текст отказа:_ {cmd['text_deny']}\n\n"
            f"_Число использований:_ {cmd['uses_count']}\n",
            message.chat.id, bot_message,
            reply_markup=command_details_keyboard(cmd_id, bot_message), parse_mode="Markdown")


# Меню команд
@bot.message_handler(commands=['my_commands'])
def my_commands(message):
    save_user(message.from_user.username, message.from_user.first_name)

    bot_message = bot.reply_to(message, "_Загрузка команд..._", parse_mode="Markdown")
    if commands_cache.get(str(message.from_user.id), None) is None or len(
            commands_cache[str(message.from_user.id)]) == 0:
        text = "😶  *У вас ещё нет команд, выберите действие*"
    else:
        text = f"📃  *Ваши команды:*\n\n"
        for cmd in commands_cache[str(message.from_user.id)]:
            text += f"   — {cmd["title"]} ([Детали](https://t.me/{BOT_USERNAME}?start={cmd["id"]}_{bot_message.message_id}))\n\n"
    bot.edit_message_text(text, message.chat.id, bot_message.message_id, parse_mode="Markdown",
                          reply_markup=commands_keyboard())


@bot.message_handler(commands=['instruction'])
def instruction_worker(message):
    bot.reply_to(message,
                 "*📋  Инструкция:*\n\n   • При использовании можно указать юзернейм цели, тогда подтверждение не потребуется\n   • Для просмотра, создания и удаления собственных команд, используй /my\\_commands\n   • В списке доступных тебе команд всегда отображаются сначала твои, потом общие, отсортированные по частоте использования\n   • Рейтинг самых используемых команд среди всех обновляется раз в 10 минут, а самых используемых среди твоих — после использования /refresh (аналогичная функция есть в меню команд)",
                 parse_mode="Markdown")
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)


@bot.message_handler(commands=['refresh'])
def refresh_worker(message):
    top_calculator(False, message.from_user.id)
    bot.reply_to(message, "*👾  Команды успешно отсортированы*", parse_mode="Markdown")


# Обработчик инлайн режима
@bot.inline_handler(lambda query: True)
def handle_inline(query):
    user_input = query.query.strip()
    user_id = str(query.from_user.id)
    user_first_name = query.from_user.first_name
    user_name = query.from_user.username

    save_user(user_name, user_first_name)

    # Убираем повторы пользовательских команд среди топовых команд
    user_commands = commands_cache.get(user_id, [])
    top_commands = commands_cache.get("top", [])
    user_cmd_ids = {cmd["id"] for cmd in user_commands}
    all_commands = user_commands + [cmd for cmd in top_commands if cmd["id"] not in user_cmd_ids]

    # Находим юзернейм получателя
    recipient_user_name = ""
    user_input_search = user_input
    if user_input:
        parts = user_input.split(" ")
        if parts[0][0] == "@":
            recipient_user_name = parts[0][1:]
            user_input_search = " ".join(parts[1:])
        elif parts[-1][0] == "@":
            recipient_user_name = parts[-1][1:]
            user_input_search = " ".join(parts[:-1])

    recipient_first_name = users_cache.get(recipient_user_name, recipient_user_name)
    results = []
    for cmd in all_commands:
        emoji = cmd["title"].split()[0] + " | "
        if (not user_input_search or user_input_search in cmd["title"].lower()) and len(results) < 50:
            # Сообщение с запросом на разрешение, нужно дождаться айдишника того кто нажмет
            if recipient_user_name == "" or user_name == recipient_user_name:
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=cmd["desc"] + " @username",
                        input_message_content=types.InputTextMessageContent(emoji +
                                                                            f"[{user_first_name}](https://t.me/{user_name}) " +
                                                                            cmd["text_inquery"],
                                                                            parse_mode="Markdown",
                                                                            disable_web_page_preview=True),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                        reply_markup=inquery_keyboard(cmd["id"], user_name)
                    )
                )
            # Сообщение без запроса, уже готовое с нужными айдишниками
            else:
                results.append(
                    types.InlineQueryResultArticle(
                        id=cmd["id"],
                        title=cmd["title"],
                        description=cmd["desc"] + f" @{recipient_user_name}",
                        input_message_content=types.InputTextMessageContent(emoji +
                                                                            f"[{user_first_name}](https://t.me/{user_name}) " +
                                                                            cmd[
                                                                                "text_response"] + f" [{recipient_first_name}](https://t.me/{recipient_user_name})",
                                                                            parse_mode="Markdown",
                                                                            disable_web_page_preview=True
                                                                            ),
                        thumbnail_url=cmd.get("thumb_url") or EMOJI_TEMPLATE.format(code=f"{ord(emoji[0]):x}"),
                        reply_markup=response_keyboard(user_name, cmd["id"])
                    )
                )
    bot.answer_inline_query(query.id, results, switch_pm_text="❤️ Инструкция",
                            switch_pm_parameter="instruction",
                            cache_time=TIMEOUT//5, is_personal=True)


# Обработчик нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def button_worker(call):
    bot.answer_callback_query(call.id)
    save_user(call.from_user.username, call.from_user.first_name)

    parts = call.data.split(" ")

    if parts[0] == "btn_accept":
        cmd_id = parts[1]
        author_msg_user_name = parts[2]
        author_msg_first_name = users_cache.get(author_msg_user_name, author_msg_user_name)
        cmd = find_cmd(cmd_id)
        emoji = cmd["title"].split()[0] + " | "

        if call.from_user.username != parts[2]:
            text = emoji + f"[{author_msg_first_name}](https://t.me/{author_msg_user_name}) " + cmd[
                "text_response"] + f" [{call.from_user.first_name}](https://t.me/{call.from_user.username})"
            bot.edit_message_text(text, inline_message_id=call.inline_message_id,
                                  reply_markup=response_keyboard(author_msg_user_name, cmd_id),
                                  parse_mode="Markdown", disable_web_page_preview=True)

    elif parts[0] == "btn_deny":
        cmd_id = parts[1]
        author_msg_user_name = parts[2]
        cmd = find_cmd(cmd_id)
        emoji = "❌ | "

        if call.from_user.username != parts[2]:
            text = emoji + f"[{call.from_user.first_name}](https://t.me/{call.from_user.username}) " + cmd["text_deny"]
            bot.edit_message_text(text, inline_message_id=call.inline_message_id,
                                  reply_markup=response_keyboard(author_msg_user_name, cmd_id),
                                  parse_mode="Markdown", disable_web_page_preview=True)

    elif parts[0] == "btn_add_command":
        if len(commands_cache.get(str(call.from_user.id), [])) < 30:
            msg = bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="*Введите название своей команды*\n\n_(Пример: _`Поцелуй`_)_",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, enter_the_name)
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="☹️  *Вы достигли максимального числа команд*",
                reply_markup=back_keyboard(call.message.message_id),
                parse_mode="Markdown"
            )
    elif parts[0] == "btn_all_right":
        successfully_create(call)
    elif parts[0] == "btn_back":
        bot_message = call.message.message_id
        if len(parts) > 2:
            cmd_id = parts[2]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = find_cmd(cmd_id)
            commands_cache[author_cmd_id].remove(cmd)
        if len(parts) > 1:
            bot_message = parts[1]

        if commands_cache.get(str(call.from_user.id), None) is None or len(commands_cache[str(call.from_user.id)]) == 0:
            text = "😶  *У вас ещё нет команд, выберите действие*"
        else:
            text = f"📃  *Ваши команды:*\n\n"
            for cmd_id in commands_cache[str(call.from_user.id)]:
                text += f"   — {cmd_id["title"]} ([Детали](https://t.me/{BOT_USERNAME}?start={cmd_id["id"]}_{bot_message}))\n\n"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=commands_keyboard(),
            parse_mode="Markdown")
    elif parts[0] == "btn_delete_command":
        try:
            global is_dirty
            cmd_id = parts[1]
            author_cmd_id = cmd_id.split("_")[0]
            cmd = find_cmd(cmd_id)
            commands_cache[author_cmd_id].remove(cmd)
            text = f"✅ *Команда успешно удалена*"
            is_dirty = True
        except:
            text = "❌ Ошибка удаления команды"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text, reply_markup=back_keyboard(call.message.message_id),
            parse_mode="Markdown")
    elif parts[0] == "btn_refresh":
        top_calculator(False, call.from_user.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="*👾  Команды успешно отсортированы*", reply_markup=back_keyboard(call.message.message_id),
            parse_mode="Markdown")


def find_cmd(cmd_id: str):
    user_id = cmd_id.split("_")[0]
    for i in commands_cache[user_id]:
        if i["id"] == cmd_id:
            cmd = i
            return cmd


# region КЛАВИАТУРЫ
# клавиатура спрашивающая принять ли предложение
def inquery_keyboard(cmd_id: str, user_name: str):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_accept = types.InlineKeyboardButton("Принять", callback_data=f"btn_accept" + f" {cmd_id}" + f" {user_name}",
                                            style="success")
    btn_deny = types.InlineKeyboardButton("Отказаться", callback_data=f"btn_deny" + f" {cmd_id}" + f" {user_name}",
                                          style="danger")
    markup.add(btn_accept, btn_deny)
    return markup


# Клавиатура предлагающая ответить на успешно совершенное действие, СЧИТАЕТ ИСПОЛЬЗОВАНИЯ
def response_keyboard(user_name: str, cmd_id):
    global is_dirty
    cmd = find_cmd(cmd_id)
    cmd["uses_count"] = str(int(cmd["uses_count"]) + 1)
    is_dirty = True

    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_response = types.InlineKeyboardButton(text="Ответить", switch_inline_query_current_chat=f"@{user_name} ")
    markup.add(btn_response)
    return markup


# Клавиатура меню команд
def commands_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_add_command = types.InlineKeyboardButton("➕ Создать команду", callback_data="btn_add_command")
    btn_refresh = types.InlineKeyboardButton("🔄️ Отсортировать команды", callback_data="btn_refresh")
    markup.add(btn_add_command, btn_refresh)
    return markup


# Клавиатура просмотра деталей отдельной команды
def command_details_keyboard(cmd_id: str, bot_message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_delete_command = types.InlineKeyboardButton("🗑️ Удалить команду",
                                                    callback_data="btn_delete_command" + f" {cmd_id}",
                                                    style="danger")
    btn_back = types.InlineKeyboardButton("⤴️ Вернуться", callback_data="btn_back" + f" {bot_message}")
    markup.add(btn_delete_command, btn_back)
    return markup


# Клавиатура возврата в меню команд
def back_keyboard(bot_message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_back = types.InlineKeyboardButton("⤴️ Вернуться", callback_data="btn_back" + f" {bot_message}")
    markup.add(btn_back)
    return markup


# Клавиатура подтверждения, что все верно или отклонения
def final_step_keyboard(cmd_id, bot_message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_all_right = types.InlineKeyboardButton("Все верно!", callback_data="btn_all_right", style="success")
    btn_back = types.InlineKeyboardButton("Отмена", callback_data="btn_back" + f" {bot_message} " + f"{cmd_id}",
                                          style="danger")
    markup.add(btn_all_right, btn_back)
    return markup


# endregion

# region ПРОЦЕСС СОЗДАНИЯ НОВОЙ КОМАНДЫ

# Ввод имени
def clean_md(text: str) -> str:
    """Удаляет символы разметки Markdown."""
    for char in ("_", "*", "`", "[", "]"):
        text = text.replace(char, "")
    return text.strip()


# Ввод названия
def enter_the_name(message):
    new_command = {"title": clean_md(message.text)}
    msg = bot.reply_to(
        message,
        "*Введите эмодзи для команды*\n\n_(Будет располагаться рядом с названием и действием)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, enter_the_emoji, new_command)


def enter_the_emoji(message, new_command):
    new_command["title"] = f"{clean_md(message.text)} {new_command['title']}"
    msg = bot.reply_to(
        message,
        "*Отправьте стикер для иконки команды*\n\n_(Или напишите /skip для пропуска)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, enter_the_sticker, new_command)


def enter_the_sticker(message, new_command):
    thumb_url = None
    if message.content_type == "sticker":
        try:
            file_info = bot.get_file(message.sticker.file_id)
            raw = bot.download_file(file_info.file_path)
            thumb_url = process_and_upload_sticker(raw)
        except Exception:
            pass
    new_command["thumb_url"] = thumb_url
    msg = bot.reply_to(message,
                       "*Введите описание команды*\n\n_(После него будет ник цели действия. Пример: _`Поцеловать`_)_",
                       parse_mode="Markdown")
    bot.register_next_step_handler(msg, enter_the_description, new_command)


# Ввод описания
def enter_the_description(message, new_command):
    new_command["desc"] = clean_md(message.text)
    msg = bot.reply_to(
        message,
        "*Введите текст запроса на действие*\n\n_(Перед ним будет твой ник. Пример: _`хочет поцеловать`_)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, enter_text_inquery, new_command)


# Ввод текста запроса
def enter_text_inquery(message, new_command):
    new_command["text_inquery"] = clean_md(message.text).lower()
    msg = bot.reply_to(
        message,
        "*Введите текст совершённого действия*\n\n_(Перед ним будет твой ник, а после него ник того, кто принял. Пример: _`поцеловал(а)`_)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, enter_text_response, new_command)


# Ввод совершившегося действия
def enter_text_response(message, new_command):
    new_command["text_response"] = clean_md(message.text).lower()
    msg = bot.reply_to(
        message,
        "*Введите текст отказа от действия*\n\n_(Перед ним будет ник того, кто отклонил. Пример: _`не хочет целоваться`_)_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, final_check, new_command)


# Финальное подтверждение
def final_check(message, new_command):
    global is_dirty
    new_command["text_deny"] = clean_md(message.text).lower()
    user_id = str(message.from_user.id)

    if user_id not in commands_cache or commands_cache[user_id] == []:
        commands_cache[user_id] = []
        commands_max_num=0
    else:
        commands_max_num = max([int(i["id"].split("_")[1]) for i in commands_cache[user_id]])+1
    print(commands_max_num)
    commands_cache[user_id].append(new_command | {"id": f"{user_id}_{commands_max_num}", "uses_count": "0"})
    bot_message = bot.reply_to(
        message,
        "_Сохранение данных..._",
        parse_mode="Markdown")
    bot.edit_message_text(
        text=f"*Проверьте правильность ввода:*\n\n"
             f"   • _Название:_ {new_command['title']}\n"
             f"   • _Описание:_ {new_command['desc']}\n"
             f"   • _Запрос:_ {new_command['text_inquery']}\n"
             f"   • _Согласие:_ {new_command['text_response']}\n"
             f"   • _Отказ:_ {new_command['text_deny']}\n",
        chat_id=bot_message.chat.id,
        message_id=bot_message.message_id,
        reply_markup=final_step_keyboard(f"{user_id}_{commands_max_num}", bot_message.message_id),
        parse_mode="Markdown"
    )

    top_calculator(False, user_id)
    is_dirty = True


# Завершение
def successfully_create(call):
    bot.edit_message_text(
        text="*Команда успешно сохранена!*",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=back_keyboard(call.message.message_id),
        parse_mode="Markdown"
    )


# endregion

# region РАБОТА С ФАЙЛАМИ

# превращение стикера в правильную пнг и загрузка на сервак
def process_and_upload_sticker(raw_bytes):
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        img.thumbnail((128, 128))
        canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        canvas.paste(img, ((128 - img.width) // 2, (128 - img.height) // 2), mask=img)

        out = io.BytesIO()
        canvas.save(out, format="PNG")

        res = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_KEY,"image": base64.b64encode(out.getvalue()).decode("utf-8")},timeout=10).json()
        return res.get("data", {}).get("url")
    except Exception:
        return None


# Добавляет ферстнейм и юзернейм в кеш
def save_user(user_name: str, user_first_name: str):
    global is_dirty
    if users_cache.get(str(user_name), None) is None:
        users_cache[user_name] = user_first_name
        is_dirty = True


# Демон поток, который синхронизирует озу и пзу, кроме того, заставляет пересчитать топы
def file_saver():
    global is_dirty
    top_calculator(True)
    while True:
        if is_dirty:
            try:
                with LOCK:
                    top_calculator(True)
                    with open(FILE_USERS_PATH + ".tmp", "w", encoding="utf-8") as f:
                        json.dump(users_cache, f, ensure_ascii=False, indent=2)
                    os.replace(FILE_USERS_PATH + ".tmp", FILE_USERS_PATH)
                    with open(FILE_COMMANDS_PATH + ".tmp", "w", encoding="utf-8") as f:
                        json.dump(commands_cache, f, ensure_ascii=False, indent=2)
                    os.replace(FILE_COMMANDS_PATH + ".tmp", FILE_COMMANDS_PATH)
                    is_dirty = False
            except Exception as e:
                print(f"Ошибка фонового сохранения: {e}")
        time.sleep(TIMEOUT)


# Вычисляет топ популярных команд
def top_calculator(is_top=False, user_id=None):
    if is_top:
        commands_cache["top"] = []
        all_commands = (cmd for author_cmd_id in commands_cache for cmd in commands_cache[author_cmd_id])
        top = heapq.nlargest(50, all_commands, key=lambda x: int(x["uses_count"]))
        for cmd in top:
            commands_cache["top"].append(cmd)
    else:
        user_id = str(user_id)
        if user_id in commands_cache:
            commands_cache[user_id] = sorted(commands_cache[user_id], key=lambda x: int(x["uses_count"]), reverse=True)


# сброс озу в пзу по кнопке остановки
def handle_exit(signum, frame):
    with open(FILE_USERS_PATH + ".tmp", "w", encoding="utf-8") as f:
        json.dump(users_cache, f, ensure_ascii=False, indent=2)
    os.replace(FILE_USERS_PATH + ".tmp", FILE_USERS_PATH)
    with open(FILE_COMMANDS_PATH + ".tmp", "w", encoding="utf-8") as f:
        json.dump(commands_cache, f, ensure_ascii=False, indent=2)
    os.replace(FILE_COMMANDS_PATH + ".tmp", FILE_COMMANDS_PATH)

    bot.stop_polling()
    sys.exit(0)


# endregion

t = threading.Thread(target=file_saver, daemon=True)
t.start()

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

bot.infinity_polling()
