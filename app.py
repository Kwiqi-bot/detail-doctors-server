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


def telegram_request(method, data):
    return requests.post(
        f"{TELEGRAM_API}/{method}",
        json=data,
        timeout=10
    )


def set_webhook():
    if not TOKEN:
        return

    webhook_url = (
        "https://detail-doctors-server.onrender.com"
        "/telegram-webhook"
    )

    try:
        telegram_request(
            "setWebhook",
            {"url": webhook_url}
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
        f"Дата и время: {date_time}"
    )

    keyboard = [
        [
            {
                "text": "Принять заявку",
                "callback_data": f"accept:{phone}"
            },
            {
                "text": "Связаться с клиентом",
                "callback_data": f"contact:{phone}"
            }
        ]
    ]

    try:

        response = telegram_request(
            "sendMessage",
            {
                "chat_id": CHAT_ID,
                "text": message,
                "reply_markup": {
                    "inline_keyboard": keyboard
                }
            }
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
        return jsonify({"ok": True})

    callback_id = callback.get("id")
    data = callback.get("data", "")

    message = callback.get("message", {})
    message_id = message.get("message_id")
    chat_id = message.get(
        "chat",
        {}
    ).get("id")

    current_text = message.get("text", "")

    user = callback.get("from", {})

    username = user.get("username")

    if username:
        employee = f"@{username}"
    else:
        employee = user.get("first_name", "Сотрудник")

    # -------------------------
    # ПРИНЯТЬ ЗАЯВКУ
    # -------------------------

    if data.startswith("accept:"):

        phone = data.replace(
            "accept:",
            "",
            1
        )

        if "Статус:" in current_text:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Эта заявка уже обработана",
                    "show_alert": True
                }
            )

            return jsonify({"ok": True})

        new_text = (
            current_text
            + "\n\n"
            "━━━━━━━━━━━━━━━━\n"
            f"Статус: ПРИНЯТА\n"
            f"Принял: {employee}"
        )

        keyboard = [
            [
                {
                    "text": "Выполнено",
                    "callback_data": f"done:{phone}"
                },
                {
                    "text": "Отменить",
                    "callback_data": f"cancel:{phone}"
                }
            ],
            [
                {
                    "text": "Связаться с клиентом",
                    "callback_data": f"contact:{phone}"
                }
            ]
        ]

        try:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Заявка принята"
                }
            )

            telegram_request(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": new_text,
                    "reply_markup": {
                        "inline_keyboard": keyboard
                    }
                }
            )

        except requests.RequestException:
            pass

    # -------------------------
    # ВЫПОЛНЕНО
    # -------------------------

    elif data.startswith("done:"):

        phone = data.replace(
            "done:",
            "",
            1
        )

        if "Статус: ПРИНЯТА" not in current_text:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Сначала нужно принять заявку",
                    "show_alert": True
                }
            )

            return jsonify({"ok": True})

        new_text = (
            current_text
            + "\n"
            "Статус: ВЫПОЛНЕНО\n"
            f"Закрыл заявку: {employee}"
        )

        try:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Заявка отмечена как выполненная"
                }
            )

            telegram_request(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": new_text
                }
            )

        except requests.RequestException:
            pass

    # -------------------------
    # ОТМЕНА
    # -------------------------

    elif data.startswith("cancel:"):

        phone = data.replace(
            "cancel:",
            "",
            1
        )

        if "Статус: ПРИНЯТА" not in current_text:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Эта заявка уже обработана",
                    "show_alert": True
                }
            )

            return jsonify({"ok": True})

        new_text = (
            current_text
            + "\n"
            "Статус: ОТМЕНЕНА\n"
            f"Отменил: {employee}"
        )

        try:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": "Заявка отменена"
                }
            )

            telegram_request(
                "editMessageText",
                {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": new_text
                }
            )

        except requests.RequestException:
            pass

    # -------------------------
    # СВЯЗАТЬСЯ С КЛИЕНТОМ
    # -------------------------

    elif data.startswith("contact:"):

        phone = data.replace(
            "contact:",
            "",
            1
        )

        try:

            telegram_request(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": f"Телефон клиента: {phone}",
                    "show_alert": True
                }
            )

        except requests.RequestException:
            pass

    return jsonify({"ok": True})


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
