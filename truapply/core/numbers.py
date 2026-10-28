import re

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def numbers(text: str) -> set[str]:
    return {match.replace(",", "") for match in NUMBER.findall(text)}


def new_numbers(original: str, tailored: str) -> list[str]:
    return sorted(numbers(tailored) - numbers(original))
