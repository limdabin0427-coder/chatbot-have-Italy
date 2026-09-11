import re

from data_loader import ITEMS


AMBIGUOUS_ITEM_PAIRS = {frozenset({"card", "cat"})}
BLOCKED_OPEN_WORDS = {
    "cancer", "sex", "sexy", "killing", "kill", "poop", "pee",
    "weapon", "gun", "knife", "drug", "drugs",
}


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


def recognition_candidates(primary, alternatives=None):
    """Return at most five unique STT candidates without inventing new speech."""
    candidates = []
    for value in [primary, *((alternatives or [])[:4])]:
        candidate = str(value or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def resolve_known_item(primary, alternatives=None):
    """Prefer a known classroom item, but stop when card/cat is genuinely unclear."""
    matches = []
    for candidate in recognition_candidates(primary, alternatives):
        if not is_have_question(candidate):
            continue
        item = find_item(candidate)
        if item:
            matches.append((candidate, item))

    matched_keys = {item["key"] for _, item in matches}
    if any(pair.issubset(matched_keys) for pair in AMBIGUOUS_ITEM_PAIRS):
        return {"status": "ambiguous", "source_text": str(primary or "").strip()}
    if matches:
        source_text, item = matches[0]
        return {"status": "known", "source_text": source_text, "item": item}
    return {"status": "unknown", "source_text": str(primary or "").strip()}


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


def is_safe_open_object_text(object_name):
    """Apply a strict local safety/shape gate before optional AI classification."""
    cleaned = clean_text(object_name)
    words = cleaned.split()
    if not cleaned or len(cleaned) > 50 or not 1 <= len(words) <= 5:
        return False
    if any(word in BLOCKED_OPEN_WORDS for word in words):
        return False
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9 '\-]*", cleaned))


def normalize_have_question(text):
    item = find_item(text)
    if item:
        return f"Do you have {item['display_name']}?"

    object_name = extract_have_object(text)
    if object_name:
        return f"Do you have {object_name}?"
    return text.strip()
