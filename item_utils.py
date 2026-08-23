import re

from data_loader import ITEMS


def clean_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def find_item(text):
    cleaned_text = clean_text(text)
    item_entries = sorted(
        ITEMS.items(),
        key=lambda item: max(
            len(alias) for alias in item[1].get("aliases", [])
        ),
        reverse=True,
    )

    for item_key, item_data in item_entries:
        search_words = item_data.get("aliases", []) + [
            item_data.get("display_name", item_key)
        ]
        for word in sorted(set(search_words), key=len, reverse=True):
            cleaned_word = clean_text(word)
            if not cleaned_word:
                continue
            pattern = rf"(?<!\w){re.escape(cleaned_word)}(?!\w)"
            if re.search(pattern, cleaned_text):
                return {
                    "key": item_key,
                    "display_name": item_data.get("display_name", item_key),
                }
    return None


def is_have_question(text):
    cleaned = clean_text(text)
    return "do you have" in cleaned and find_item(text) is not None


def normalize_have_question(text):
    item = find_item(text)
    if not item:
        return text.strip()
    return f"Do you have {item['display_name']}?"
