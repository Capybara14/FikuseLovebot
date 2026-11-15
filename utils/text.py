def clean_md(text: str) -> str:
    """Удаляет символы разметки Markdown."""
    for char in ("_", "*", "`", "[", "]"):
        text = text.replace(char, "")
    return text.strip()
