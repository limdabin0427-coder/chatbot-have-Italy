def get_item_answer(character, item_key):
    return character.get("inventory", {}).get(item_key, "no")


def make_item_response(answer, display_name):
    if answer == "yes":
        return f"Yes, I do. I have {display_name}."
    return f"No, I don't. I don't have {display_name}."
