import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


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

    name = data.get("name", "")
    phone = data.get("phone", "")
    service = data.get("service", "")
    comment = data.get("comment", "")

    if not name or not phone or not service:
        return jsonify({
            "success": False,
            "error": "Не заполнены обязательные поля"
        }), 400

    message = (
        "НОВАЯ ЗАЯВКА С САЙТА\n\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Услуга: {service}\n"
        f"Комментарий: {comment}"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )

        if response.ok:
            return jsonify({"success": True})

        return jsonify({
            "success": False,
            "error": "Telegram не принял сообщение"
        }), 500

    except requests.RequestException:
        return jsonify({
            "success": False,
            "error": "Ошибка соединения с Telegram"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
