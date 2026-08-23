import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_json(file_name):
    file_path = DATA_DIR / file_name
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"{file_name} 파일을 찾을 수 없습니다."
        ) from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{file_name}의 JSON 형식이 올바르지 않습니다. "
            f"{error.lineno}번째 줄을 확인해주세요."
        ) from error


CHARACTERS = load_json("characters.json")
ITEMS = load_json("items.json")
