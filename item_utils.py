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


def extract_have_object(text):
    cleaned = clean_text(text)
    match = re.search(r"\bdo\s+you\s+have\b\s+(.+)$", cleaned)
    if not match:
        return None

    object_name = match.group(1).strip()
    object_name = re.sub(r"^(?:a|an|the)\s+", "", object_name)
    return object_name or None


def is_have_question(text):
    return extract_have_object(text) is not None


def normalize_have_question(text):
    item = find_item(text)
    if item:
        return f"Do you have {item['display_name']}?"

    object_name = extract_have_object(text)
    if object_name:
        return f"Do you have {object_name}?"
    return text.strip()
