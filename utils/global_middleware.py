import time
from collections import defaultdict, deque
from aiogram import BaseMiddleware
import config


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 30, window: int = 60):
        self.limit = limit
        self.window = window
        self.history: dict[int, deque[float]] = defaultdict(deque)

    async def __call__(self, handler, event, data: dict):
        user = data.get("event_from_user")
        if not user or user.is_bot or user.id in config.ADMINS:
            return await handler(event, data)

        now = time.monotonic()
        timestamps = self.history[user.id]
        while timestamps and now - timestamps[0] > self.window:
            timestamps.popleft()

        if len(timestamps) >= self.limit:
            return

        timestamps.append(now)
        return await handler(event, data)


async def ban_middleware(handler, event, data: dict):
    user = data.get("event_from_user")
    if user and data["storage"].users_cache.get(str(user.id), {}).get("is_banned"):
        return
    return await handler(event, data)


async def save_user_middleware(handler, event, data: dict):
    user = data.get("event_from_user")
    if user and not user.is_bot:
        storage = data["storage"]
        user_id = str(user.id)
        user_name = user.username.lower() if user.username else None
        user_first_name = user.first_name

        cached = storage.users_cache.get(user_id)
        if not cached or cached.get("user_name") != user_name or cached.get("user_first_name") != user_first_name:
            if not cached:
                storage.users_cache[user_id] = {}
            storage.users_cache[user_id]["user_name"] = user_name
            storage.users_cache[user_id]["user_first_name"] = user_first_name

    return await handler(event, data)
