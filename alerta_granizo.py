import os
import requests

# Credenciales de Telegram (desde Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Coordenadas exactas a vigilar
LATITUD = -34.5950
LONGITUD = -58.6350

HISTORIAL_ALERTAS = "alertas_enviadas.txt"


def cargar_alertas_notificadas():
    if not os.path.exists(HISTORIAL_ALERTAS):
        return set()
    with open(HISTORIAL_ALERTAS, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_alerta_notificada(evento_id):
    with open(HISTORIAL_ALERTAS, "a", encoding="utf-8") as f:
        f.write(f"{evento_id}\n")


def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("-> Alerta despachada a Telegram exitosamente.")
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")


def verificar_tiempo():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Variables de entorno de Telegram ausentes.")
        return

    # Consulta a Open-Meteo para las próximas 2 horas en tus coordenadas
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LATITUD}&longitude={LONGITUD}"
        f"&current=weather_code,precipitation,showers"
        f"&hourly=weather_code,precipitation_probability,precipitation"
        f"&forecast_hours=3&timezone=America%2FArgentina%2FBuenos_Aires"
    )

    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"Error al consultar el servicio meteorológico: {e}")
        return

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    current_code = current.get("weather_code", 0)
    hourly_codes = hourly.get("weather_code", [])
    hourly_times = hourly.get("time", [])

    alertas_previas = cargar_alertas_notificadas()

    # Códigos WMO de tormenta con granizo:
    # 96: Tormenta con granizo leve/moderado
    # 99: Tormenta severa con granizo fuerte
    # 95: Tormenta eléctrica fuerte (alerta preventiva)
    amenaza_granizo = False
    motivo = ""
    evento_id = ""

    # 1. Chequeo del momento actual
    if current_code in [96, 99]:
        amenaza_granizo = True
        motivo = "Tormenta con caída de granizo en curso o inminente."
        evento_id = f"now_{current.get('time')}_{current_code}"
    elif current_code == 95:
        # Si hay tormenta fuerte, revisamos si la precipitación es violenta
        if current.get("precipitation", 0) > 10.0:
            amenaza_granizo = True
            motivo = "Tormenta eléctrica severa con alta probabilidad de granizo."
            evento_id = f"storm_{current.get('time')}"

    # 2. Chequeo en la ventana de las próximas 1 a 2 horas si no hay evento actual
    if not amenaza_granizo and hourly_codes:
        for t, code in zip(hourly_times, hourly_codes):
            if code in [96, 99]:
                amenaza_granizo = True
                hora_formateada = t.split("T")[-1]
                motivo = f"Pronóstico de tormenta con granizo previsto alrededor de las {hora_formateada} hs."
                evento_id = f"forecast_{t}_{code}"
                break

    if amenaza_granizo:
        if evento_id in alertas_previas:
            print("Alerta ya notificada anteriormente.")
            return

        mensaje = (
            "⚠️ *ALERTA METEOROLÓGICA DE GRANIZO*\n\n"
            f"📌 *Diagnóstico:* {motivo}\n\n"
            "🚗 *Revisá si el auto está protegido bajo techo.*"
        )
        enviar_mensaje_telegram(mensaje)
        guardar_alerta_notificada(evento_id)
    else:
        print(f"Condiciones estables. Código actual: {current_code}. Sin riesgo de granizo inminente.")


if __name__ == "__main__":
    verificar_tiempo()
