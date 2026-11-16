import asyncio
import heapq
import json
import os

import config


def _write_file(path: str, data: str) -> None:
    with open(path + ".tmp", "w", encoding="utf-8") as f: f.write(data)
    os.replace(path + ".tmp", path)


class Storage:
    def __init__(self, users_path: str, commands_path: str, timeout: int) -> None:
        self.users_path = users_path
        self.commands_path = commands_path
        self.timeout = timeout

        self.commands_cache = {}
        self.users_cache = {}
        self.usernames_cache = {}
        self.commands_top = []

    def load_cache(self) -> None:
        if os.path.exists(self.commands_path):
            with open(self.commands_path, "r", encoding="utf-8") as f:
                self.commands_cache = json.load(f)
        if os.path.exists(self.users_path):
            with open(self.users_path, "r", encoding="utf-8") as f:
                self.users_cache = json.load(f)
        for i in self.users_cache.values():
            if i.get("user_name"):
                self.usernames_cache[i["user_name"]] = i["user_first_name"]
        self.top_calculator()

    async def save_cache(self, once: bool = False) -> None:
        while True:
            if not once: await asyncio.sleep(self.timeout)
            try:
                self.top_calculator()
                await asyncio.to_thread(_write_file, self.users_path,
                                        json.dumps(self.users_cache, ensure_ascii=False, indent=2))
                await asyncio.to_thread(_write_file, self.commands_path,
                                        json.dumps(self.commands_cache, ensure_ascii=False, indent=2))
                for i in self.users_cache.values():
                    if i.get("user_name"):
                        self.usernames_cache[i["user_name"]] = i["user_first_name"]
            except Exception as e:
                print(f"Ошибка фонового сохранения: {e}")
            if once: break


    # Добавляет единичку к использованию команды
    def increment_uses(self, cmd_id: str):
        user_id = cmd_id.split("_")[0]
        cmd = self.find_cmd(cmd_id)
        if not cmd: return
        self.commands_cache[user_id].remove(cmd)
        cmd["uses_count"] = str(int(cmd.get("uses_count", 0)) + 1)
        self.commands_cache[user_id].append(cmd)
        self.commands_sort(user_id)

    def find_cmd(self, cmd_id: str):
        user_id = cmd_id.split("_")[0]
        for i in self.commands_cache[user_id]:
            if i["id"] == cmd_id:
                return i
        return None

    # Вычисляет топ популярных команд
    def top_calculator(self):
        self.commands_top = []
        all_commands = (cmd for author_cmd_id in self.commands_cache for cmd in self.commands_cache[author_cmd_id])
        top = heapq.nlargest(100, all_commands, key=lambda x: int(x["uses_count"]))
        for cmd in top:
            self.commands_top.append(cmd)

    # сортирует команды пользователя
    def commands_sort(self, user_id: str):
        if user_id in self.commands_cache:
            self.commands_cache[user_id] = sorted(self.commands_cache[user_id], key=lambda x: int(x["uses_count"]),
                                                  reverse=True)

    #Банит пользователя и удаляет все его команды
    def set_ban(self, user_id: str, status: bool):
        if status and user_id in config.ADMINS:
            return
        if status:
            self.users_cache[user_id]["is_banned"] = True
            self.commands_cache[user_id] = []
            self.top_calculator()
        else:
            self.users_cache[user_id]["is_banned"] = False