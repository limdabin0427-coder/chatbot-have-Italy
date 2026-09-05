import json
import os
import re
import traceback
from datetime import datetime

import gspread
from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from google.oauth2.service_account import Credentials
from openai import OpenAI

from config import (
    CHATBOT_ID,
    ENABLE_GOOGLE_SHEETS,
    FLASK_SECRET_KEY,
    GOOGLE_SERVICE_ACCOUNT_ENV,
    LESSON_TYPE,
    MAX_HISTORY_MESSAGES,
    MAX_RESPONSE_TOKENS,
    MODEL_NAME,
    OPENAI_API_KEY_ENV,
    SPREADSHEET_ID,
    Stage,
    TEMPERATURE,
)
from data_loader import CHARACTERS
from dialogue_manager import get_item_answer, make_item_response
from item_utils import clean_text, find_item, is_have_question, normalize_have_question


app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = FLASK_SECRET_KEY
CORS(app)

CHARACTER = CHARACTERS[CHATBOT_ID]
CHARACTER_NAME = CHARACTER["name"]
COUNTRY = CHARACTER["country"]
SHEET_TAB = CHARACTER.get("sheet_tab", CHATBOT_ID)
ENDING_MESSAGE = CHARACTER["ending_message"]

openai_key = os.environ.get(OPENAI_API_KEY_ENV)
openai_client = OpenAI(api_key=openai_key) if openai_key else None


sheet = None
if ENABLE_GOOGLE_SHEETS:
    try:
        raw_creds = os.environ.get(GOOGLE_SERVICE_ACCOUNT_ENV)
        if raw_creds:
            info = json.loads(raw_creds)
            creds = Credentials.from_service_account_info(
                info,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )
            spreadsheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID)
            try:
                sheet = spreadsheet.worksheet(SHEET_TAB)
            except gspread.exceptions.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title=SHEET_TAB, rows=1000, cols=9)
            if not sheet.get_all_values():
                sheet.append_row([
                    "시간", "번호", "이름", "학생발화(보정)", "원본발화",
                    "루카응답", "단계", "나라", "수업유형",
                ])
            print(f"✅ 구글 시트 연결: {SHEET_TAB} / {LESSON_TYPE}")
        else:
            print("⚠️ GOOGLE_SERVICE_ACCOUNT 환경변수 없음")
    except Exception as error:
        print(f"❌ 구글 시트 연결 실패: {error}")
        traceback.print_exc()


def normalize_stage(stage):
    aliases = {
        "await_greeting": Stage.WAIT_GREETING.value,
        "WAIT_GREETING": Stage.WAIT_GREETING.value,
    }
    return aliases.get(stage, stage or Stage.WAIT_GREETING.value)


def safe_login_value(value, fallback=""):
    value = str(value or "").strip()
    value = re.sub(r"[<>\r\n\t]", "", value)
    return value[:30] or fallback


def is_greeting(message):
    text = clean_text(message)
    greetings = ["hello", "hi", "hey", "good morning", "안녕"]
    return any(word in text for word in greetings)


def parse_yes_no(message):
    text = clean_text(message)
    negatives = ["no", "no i dont", "no i don t", "i dont", "i don t", "do not", "아니", "없어"]
    positives = ["yes", "yes i do", "i do", "응", "네", "있어"]
    if any(value in text for value in negatives):
        return "no"
    if any(value in text for value in positives):
        return "yes"
    return None


def feeling_reply(message):
    text = clean_text(message)
    if any(word in text for word in ["tired", "sleepy", "sad", "not good"]):
        return "I see. Let's study together!"
    if any(word in text for word in ["happy", "great", "good", "fine"]):
        return "Good! Now, let's study together!"
    return "Okay! Let's study together!"


def call_gpt(system_prompt, user_message, fallback):
    """제한된 생성형 피드백. 실패하면 수업 흐름을 지키는 기본 응답을 사용한다."""
    if not openai_client:
        return fallback
    try:
        result = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_RESPONSE_TOKENS,
        )
        reply = (result.choices[0].message.content or "").strip()
        return reply or fallback
    except Exception as error:
        print(f"❌ OpenAI 호출 실패: {error}")
        return fallback


def ai_feeling_reply(message):
    fallback = feeling_reply(message)
    prompt = f"""
You are {CHARACTER_NAME}, a friendly 10-year-old child from {COUNTRY}.
A Korean grade-3 beginner has answered "How are you today?"
Respond to the feeling in exactly one very short A1 English sentence.
Use no more than 5 words. Do not ask a question. Do not correct grammar.
Do not use emojis, explanations, Korean, or quotation marks.
""".strip()
    return call_gpt(prompt, message, fallback)


def ai_classify_yes_no(message):
    prompt = """
Classify a Korean grade-3 beginner's answer to a Do you have...? question.
Return exactly one lowercase word: yes, no, or unknown.
Accept short, imperfect, or mixed Korean-English answers.
""".strip()
    result = call_gpt(prompt, message, "unknown").lower().strip(" .!?\"'")
    return result if result in {"yes", "no"} else None


def ai_scaffold_reply(message, example):
    fallback = f'Good try! Say, "{example}"'
    prompt = f"""
You are {CHARACTER_NAME}, a friendly AI partner for Korean grade-3 English beginners.
The learner is doing a short controlled speaking task about "Do you have...?"
The learner said: {message}
Give supportive corrective feedback in one or two very short A1 sentences.
End by giving this exact model expression: {example}
Do not explain grammar. Do not use Korean or emojis.
""".strip()
    return call_gpt(prompt, message, fallback)


def save_log(corrected, original, reply, stage):
    if sheet is None:
        return
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([
            now,
            session.get("student_number", ""),
            session.get("student_name", ""),
            corrected,
            original,
            reply,
            stage,
            COUNTRY,
            LESSON_TYPE,
        ])
    except Exception as error:
        print(f"❌ 시트 저장 실패: {error}")
        traceback.print_exc()


def respond(reply, popup, next_stage, fireworks=False, original="", corrected=None, speech_reply=None):
    corrected = corrected if corrected is not None else original
    history = session.get("chat_history", [])
    if corrected:
        history.append({"role": "user", "content": corrected})
    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history[-MAX_HISTORY_MESSAGES:]
    session.modified = True
    save_log(corrected, original, reply, next_stage)
    return jsonify({
        "reply": reply,
        "speech_reply": speech_reply or reply,
        "popup": popup,
        "stage": next_stage,
        "fireworks": fireworks,
        "recognized_text": corrected,
    })


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def chatbot_config():
    images = CHARACTER.get("images", {})
    character_images = images.get("character", {})
    tts = CHARACTER.get("tts", {})
    return jsonify({
        "chatbotId": CHATBOT_ID,
        "characterName": CHARACTER_NAME,
        "country": COUNTRY,
        "landingTitle": CHARACTER.get("landing_title", "Hello, Korea!"),
        "gif": {
            "greeting": character_images.get("greeting", "greeting.gif"),
            "speaking": character_images.get("speaking", "speaking.gif"),
            "yes": character_images.get("yes", "yes.gif"),
            "no": character_images.get("no", "no.gif"),
        },
        "backgrounds": images.get("backgrounds", []),
        "flagImg": images.get("flag", ""),
        "tts": {
            "gender": tts.get("gender", CHARACTER.get("gender", "male")),
            "childMode": tts.get("child_mode", True),
            "rate": tts.get("rate", 0.85),
            "pitch": tts.get("pitch", 1.35),
        },
        "finaleMsg": CHARACTER.get("finale_message", "Come visit Italy next time!"),
    })


@app.route("/api/start", methods=["POST"])
def start_chat():
    data = request.get_json(force=True, silent=True) or {}
    student_number = safe_login_value(data.get("student_number"), "00")
    student_name = safe_login_value(data.get("student_name"), "친구")

    session.clear()
    session["student_number"] = student_number
    session["student_name"] = student_name
    session["asked_items"] = []
    session["chat_history"] = []

    display_reply = f"Hi, {student_name}! {CHARACTER['intro_message']}"
    return respond(
        reply=display_reply,
        speech_reply=CHARACTER["intro_speech"],
        popup=f"{CHARACTER_NAME}에게 영어로 인사해 보세요!",
        next_stage=Stage.WAIT_GREETING.value,
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    original = (data.get("message") or "").strip()
    stage = normalize_stage((data.get("stage") or "").strip())

    if not original:
        return respond("Please say that again.", "다시 한 번 말해 보세요.", stage, original=original)

    if stage == Stage.WAIT_GREETING.value:
        if not is_greeting(original):
            return respond(
                'Please say, "Hello!"',
                f'{CHARACTER_NAME}에게 "Hello!"라고 인사해 보세요.',
                stage,
                original=original,
            )
        return respond(
            "Hello! How are you today?",
            "오늘의 기분을 영어로 말해 보세요.",
            Stage.WAIT_FEELING.value,
            original=original,
            corrected="Hello!",
        )

    if stage == Stage.WAIT_FEELING.value:
        return respond(
            feeling_reply(original),
            "활동지의 물음을 보고 질문해 보세요.",
            Stage.STUDENT_QUESTION_1.value,
            original=original,
        )

    question_stages = {
        Stage.STUDENT_QUESTION_1.value: (
            Stage.STUDENT_QUESTION_2.value,
            "활동지를 보고 두 번째 물품을 물어보세요.",
            " Ask me one more question.",
        ),
        Stage.STUDENT_QUESTION_2.value: (
            Stage.STUDENT_QUESTION_3.value,
            "물품을 하나 골라 마지막 질문을 해 보세요.",
            " Great! Choose one more item and ask me.",
        ),
        Stage.STUDENT_QUESTION_3.value: (Stage.END.value, None, f" {ENDING_MESSAGE}"),
    }

    if stage in question_stages:
        item = find_item(original)
        if not item:
            return respond(
                ai_scaffold_reply(original, "Do you have a ruler?"),
                "활동지의 물품을 보고 질문해 보세요.",
                stage,
                original=original,
            )
        if not is_have_question(original):
            example = f"Do you have {item['display_name']}?"
            return respond(
                ai_scaffold_reply(original, example),
                f'"{example}"라고 다시 말해 보세요.',
                stage,
                original=original,
            )

        corrected = normalize_have_question(original)
        asked_items = session.get("asked_items", [])
        if item["key"] in asked_items:
            return respond(
                "You already asked me that. Please choose a different item.",
                "다른 물품을 골라 질문해 보세요.",
                stage,
                original=original,
                corrected=corrected,
            )

        asked_items.append(item["key"])
        session["asked_items"] = asked_items
        next_stage, popup, ending = question_stages[stage]
        answer = get_item_answer(CHARACTER, item["key"])
        reply = make_item_response(answer, item["display_name"]) + ending
        return respond(
            reply,
            popup,
            next_stage,
            fireworks=next_stage == Stage.END.value,
            original=original,
            corrected=corrected,
        )

    return respond(ENDING_MESSAGE, None, Stage.END.value, fireworks=True, original=original)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
