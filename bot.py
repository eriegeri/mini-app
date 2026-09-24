import os
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")


# Prezzi:
# I servizi esistenti rimangono invariati.
# Catch Em = 50 Telegram Stars.
SERVICES = {
    "Sexchat": 2000,
    "Video personalizzato": 2000,
    "Videochiamata": 4000,
    "Incontri": 15000,
    "Catch Em": 50
}


def telegram_request(method, payload):
    """
    Invia una richiesta alle API Telegram.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    response = requests.post(
        url,
        json=payload,
        timeout=20
    )

    return response.json()


@app.route("/")
def home():
    return "Bot backend attivo"


# =========================================================
# CREAZIONE PAGAMENTO
# =========================================================

@app.route("/create-invoice", methods=["POST"])
def create_invoice():

    data = request.get_json() or {}

    service = data.get("service")

    if service not in SERVICES:
        return jsonify({
            "error": "Servizio non valido"
        }), 400


    # =====================================================
    # INCONTRI - PAGAMENTO CARTA / REDSYS
    # =====================================================

    if service == "Incontri":

        provider_token = os.environ.get(
            "REDSYS_TEST_TOKEN"
        )

        if not provider_token:

            return jsonify({
                "error": "Token Redsys non configurato"
            }), 500


        payload = {

            "title": service,

            "description":
                "Acquisto: Incontri",

            "payload":
                service,

            "provider_token":
                provider_token,

            "currency":
                "EUR",

            "prices": [
                {
                    "label": service,
                    "amount": 15000
                }
            ]
        }


    # =====================================================
    # TELEGRAM STARS
    # =====================================================

    else:

        stars = SERVICES[service]


        # Per i prodotti digitali / accesso al gioco
        # Telegram Stars usa la valuta XTR.
        payload = {

            "title":
                service,

            "description":
                (
                    "Accesso a una partita di Catch 'Em."
                    if service == "Catch Em"
                    else f"Acquisto: {service}"
                ),

            "payload":
                service,

            "provider_token":
                "",

            "currency":
                "XTR",

            "prices": [
                {
                    "label":
                        (
                            "1 partita"
                            if service == "Catch Em"
                            else service
                        ),

                    "amount":
                        stars
                }
            ]
        }


    result = telegram_request(
        "createInvoiceLink",
        payload
    )


    if not result.get("ok"):

        print(
            "Errore Telegram:",
            result
        )

        return jsonify({
            "error": result
        }), 500


    return jsonify({
        "invoice_url":
            result["result"]
    })


# =========================================================
# WEBHOOK TELEGRAM
# =========================================================

@app.route(
    "/telegram-webhook",
    methods=["POST"]
)
def telegram_webhook():

    update = request.get_json() or {}


    # =====================================================
    # PRE-CHECKOUT
    # =====================================================

    if "pre_checkout_query" in update:

        query = update[
            "pre_checkout_query"
        ]

        query_id = query["id"]

        payload = {
            "pre_checkout_query_id":
                query_id,

            "ok":
                True
        }


        result = telegram_request(
            "answerPreCheckoutQuery",
            payload
        )


        print(
            "Pre-checkout:",
            result
        )


    # =====================================================
    # PAGAMENTO COMPLETATO
    # =====================================================

    if "message" in update:

        message = update["message"]

        payment = message.get(
            "successful_payment"
        )


        if payment:

            print(
                "Pagamento ricevuto:",
                payment
            )


            currency = payment.get(
                "currency"
            )

            total_amount = payment.get(
                "total_amount"
            )

            invoice_payload = payment.get(
                "invoice_payload"
            )


            # =================================================
            # TELEGRAM STARS
            # =================================================

            if currency == "XTR":

                amount_text = (
                    f"{total_amount} ⭐"
                )

            # =================================================
            # EURO
            # =================================================

            else:

                amount_text = (
                    f"{total_amount / 100:.2f} €"
                )


            # =================================================
            # DETERMINAZIONE SERVIZIO
            # =================================================

            service_name = (
                invoice_payload
                or "Servizio non specificato"
            )


            # =================================================
            # MESSAGGIO ADMIN
            # =================================================

            if ADMIN_CHAT_ID:

                admin_message = (
                    "💰 PAGAMENTO RICEVUTO!\n\n"
                    f"📦 Prodotto: {service_name}\n"
                    f"💳 Importo: {amount_text}\n"
                    f"💱 Valuta: {currency}\n\n"
                    f"🧾 Payload: {invoice_payload}"
                )


                requests.post(
                    (
                        f"https://api.telegram.org/"
                        f"bot{BOT_TOKEN}/sendMessage"
                    ),

                    json={
                        "chat_id":
                            ADMIN_CHAT_ID,

                        "text":
                            admin_message
                    },

                    timeout=20
                )


    return "OK"


# =========================================================
# AVVIO SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )