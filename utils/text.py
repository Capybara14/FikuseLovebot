def clean_md(text: str) -> str:
    """Удаляет символы разметки Markdown."""
    for char in ("_", "*", "`", "[", "]"):
        text = text.replace(char, "")
    return text.strip()

def html_link_to_user(user_id=None, user_name=None, chat: bool = False) -> str:
    if chat:
        return f'<a href="https://t.me/{user_name}">' if user_name else '<a>'
    if user_name:
        return f'<a href="https://t.me/{user_name}">'
    if user_id is not None:
        return f'<a href="tg://user?id={user_id}">'
    return '<a>'