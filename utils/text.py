def clean_md(text: str) -> str:
    """Удаляет символы разметки Markdown."""
    for char in ("_", "*", "`", "[", "]"):
        text = text.replace(char, "")
    return text.strip()

def html_link_to_user(user_id=None, user_name=None, chat:bool=False)->str:
    if chat:
        return f'<a{f"href=https://t.me/{user_name}" if user_name else f""}>'
    return f'<a href="{f"https://t.me/{user_name}" if user_name else f"tg://user?id={user_id}"}">'