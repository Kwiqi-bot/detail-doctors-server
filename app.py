import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def send_telegram_message(text, keyboard=None):

    data = {
        "chat_id": CHAT_ID,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    response = requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=data,
        timeout=10
    )

    return response


def set_webhook():

    if not TOKEN:
        return

    webhook_url = (
        "https://detail-doctors-server.onrender.com"
        "/telegram-webhook"
    )

    try:
        requests.post(
            f"{TELEGRAM_API}/setWebhook",
            json={
                "url": webhook_url
            },
            timeout=10
        )
    except requests.RequestException:
        pass


@app.route("/")
def home():

    return "Detail Doctors Telegram Server работает!"


@app.route("/send", methods=["POST"])
def send_message():

    if not TOKEN or not CHAT_ID:
        return jsonify({
            "success": False,
            "error": "Telegram secrets не настроены"
        }), 500

    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    service = data.get("service", "").strip()
    comment = data.get("comment", "").strip()

    if not name or not phone or not service:

        return jsonify({
            "success": False,
            "error": "Не заполнены обязательные поля"
        }), 400

    # Время Оренбурга
    now = datetime.now(
        ZoneInfo("Asia/Yekaterinburg")
    )

    date_time = now.strftime("%d.%m.%Y %H:%M")

    message = (
        "НОВАЯ ЗАЯВКА\n"
        "━━━━━━━━━━━━━━━━\n\n"

        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Услуга: {service}\n"
        f"Комментарий: {comment or 'Не указан'}\n\n"

        "━━━━━━━━━━━━━━━━\n"
        f"Дата и время: {date_time}\n"
    )

    keyboard = [[
        {
            "text": "Принять заявку",
            "callback_data": f"accept:{phone}"
        },
        {
            "text": "Связаться с клиентом",
            "callback_data": f"contact:{phone}"
        }
    ]]

    try:

        response = send_telegram_message(
            message,
            keyboard
        )

        if response.ok:

            return jsonify({
                "success": True
            })

        return jsonify({
            "success": False,
            "error": "Telegram не принял сообщение"
        }), 500

    except requests.RequestException:

        return jsonify({
            "success": False,
            "error": "Ошибка соединения с Telegram"
        }), 500


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():

    update = request.get_json(
        silent=True
    ) or {}

    callback = update.get("callback_query")

    if not callback:
        return jsonify({
            "ok": True
        })

    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})

    chat_id = message.get(
        "chat",
        {}
    ).get("id")

    message_id = message.get("message_id")

    if data.startswith("accept:"):

        phone = data.replace(
            "accept:",
            "",
            1
        )

        text = (
            "Заявка принята.\n\n"
            f"Телефон клиента: {phone}"
        )

        try:

            requests.post(
                f"{TELEGRAM_API}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_id,
                    "text": "Заявка принята",
                    "show_alert": False
                },
                timeout=10
            )

            requests.post(
                f"{TELEGRAM_API}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {
                        "inline_keyboard": [[
                            {
                                "text": "Заявка принята",
                                "callback_data": "accepted"
                            },
                            {
                                "text": "Связаться с клиентом",
                                "callback_data": f"contact:{phone}"
                            }
                        ]]
                    }
                },
                timeout=10
            )

            send_telegram_message(text)

        except requests.RequestException:
            pass

    elif data.startswith("contact:"):

        phone = data.replace(
            "contact:",
            "",
            1
        )

        try:

            requests.post(
                f"{TELEGRAM_API}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_id,
                    "text": f"Телефон: {phone}",
                    "show_alert": True
                },
                timeout=10
            )

        except requests.RequestException:
            pass

    return jsonify({
        "ok": True
    })


# Устанавливаем webhook при запуске
set_webhook()


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
