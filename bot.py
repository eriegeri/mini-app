import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

SERVICES = {
    "Sexchat": 2000,
    "Video personalizzato": 2000,
    "Videochiamata": 4000,
    "Incontri": 15000
}

@app.route("/")
def home():
    return "Bot backend attivo"


@app.route("/create-invoice", methods=["POST"])
def create_invoice():
    data = request.get_json() or {}
    service = data.get("service")

    if service not in SERVICES:
        return jsonify({"error": "Servizio non valido"}), 400

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"

    # Pagamento con carta tramite Redsys
    if service == "Incontri":
        provider_token = os.environ.get("REDSYS_TEST_TOKEN")

        if not provider_token:
            return jsonify({"error": "Token Redsys non configurato"}), 500

        payload = {
            "title": service,
            "description": "Acquisto: Incontri",
            "payload": service,
            "provider_token": provider_token,
            "currency": "EUR",
            "prices": [
                {
                    "label": service,
                    "amount": 15000
                }
            ]
        }

    # Pagamento con Telegram Stars
    else:
        stars = SERVICES[service]

        payload = {
            "title": service,
            "description": f"Acquisto: {service}",
            "payload": service,
            "provider_token": "",
            "currency": "XTR",
            "prices": [
                {
                    "label": service,
                    "amount": stars
                }
            ]
        }

    response = requests.post(url, json=payload)
    result = response.json()

    if not result.get("ok"):
        return jsonify({"error": result}), 500

    return jsonify({"invoice_url": result["result"]})


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json() or {}

    if "pre_checkout_query" in update:
        query_id = update["pre_checkout_query"]["id"]

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/answerPreCheckoutQuery",
            json={
                "pre_checkout_query_id": query_id,
                "ok": True
            }
        )

    if "message" in update:
        payment = update["message"].get("successful_payment")

        if payment:
            print("Pagamento ricevuto:", payment)

            admin_chat_id = os.environ.get("ADMIN_CHAT_ID")

            if admin_chat_id:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": admin_chat_id,
                        "text": (
                            "💰 Pagamento ricevuto!\n\n"
                            "📦 Prodotto: Incontri\n"
                            "💶 Importo: 150 €"
                        )
                    }
                )

    return "OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)