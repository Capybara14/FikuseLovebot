def gender_match_text(text: str, gender: str) -> str:
    new_text = text

    if gender == "None":
        return new_text

    if "(её)" in text:
        if gender == "Мужской":
            new_text = text.replace("(её)", "")
        if gender == "Женский":
            new_text = text.replace("его(её)", "её")
    if "(а)" in text:
        if gender == "Мужской":
            new_text = text.replace("(а)", "")
        if gender == "Женский":
            new_text = text.replace("(а)", "а")
    if "(лась)" in text:
        if gender == "Мужской":
            new_text = text.replace("(лась)", "")
        if gender == "Женский":
            new_text = text.replace("лся(лась)", "лась")

    return new_text
