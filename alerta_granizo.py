import os
import requests

# Credenciales de Telegram (desde Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Puntos geográficos a monitorear
UBICACIONES = {
    "CASA": {"lat": -34.6150, "lon": -58.6350},
    "MORON": {"lat": -34.6534, "lon": -58.6198},
    "LELOIR": {"lat": -34.6133, "lon": -58.6853},
    "CHACARITA": {"lat": -34.5875, "lon": -58.4550},
    "PALERMO": {"lat": -34.5780, "lon": -58.4265},
    "MICROCENTRO": {"lat": -34.6037, "lon": -58.3750},
}

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


def evaluar_zona(nombre_zona, coords, alertas_previas):
    lat = coords["lat"]
    lon = coords["lon"]

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=weather_code,precipitation,showers"
        f"&hourly=weather_code,precipitation_probability,precipitation"
        f"&forecast_hours=3&timezone=America%2FArgentina%2FBuenos_Aires"
    )

    try:
        res = requests.get(url, timeout=12)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[{nombre_zona}] Error al consultar API: {e}")
        return

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    current_code = current.get("weather_code", 0)
    hourly_codes = hourly.get("weather_code", [])
    hourly_times = hourly.get("time", [])

    amenaza_granizo = False
    motivo = ""
    evento_id = ""

    # Códigos WMO de tormenta con granizo:
    # 96: Tormenta con granizo leve/moderado
    # 99: Tormenta severa con granizo fuerte
    # 95: Tormenta eléctrica fuerte
    if current_code in [96, 99]:
        amenaza_granizo = True
        motivo = "Tormenta con caída de granizo en curso o inminente."
        evento_id = f"{nombre_zona}_now_{current.get('time')}_{current_code}"
    elif current_code == 95 and current.get("precipitation", 0) > 10.0:
        amenaza_granizo = True
        motivo = "Tormenta eléctrica severa con alta probabilidad de granizo."
        evento_id = f"{nombre_zona}_storm_{current.get('time')}"

    if not amenaza_granizo and hourly_codes:
        for t, code in zip(hourly_times, hourly_codes):
            if code in [96, 99]:
                amenaza_granizo = True
                hora = t.split("T")[-1]
                motivo = f"Pronóstico de tormenta con granizo estimado a las {hora} hs."
                evento_id = f"{nombre_zona}_forecast_{t}_{code}"
                break

    if amenaza_granizo:
        if evento_id in alertas_previas:
            print(f"[{nombre_zona}] Alerta ({evento_id}) ya notificada.")
            return

        mensaje = (
            f"⚠️ *ALERTA DE GRANIZO: {nombre_zona}*\n\n"
            f"📍 *Zona afectada:* {nombre_zona}\n"
            f"📌 *Diagnóstico:* {motivo}\n\n"
            "🚗 *Revisá si el auto está bajo techo en esa zona.*"
        )
        enviar_mensaje_telegram(mensaje)
        guardar_alerta_notificada(evento_id)
    else:
        print(f"[{nombre_zona}] Estable (código {current_code}). Sin riesgo.")


def verificar_tiempo():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Variables de entorno ausentes.")
        return

    alertas_previas = cargar_alertas_notificadas()

    for zona, coords in UBICACIONES.items():
        evaluar_zona(zona, coords, alertas_previas)


if __name__ == "__main__":
    # Línea temporal de prueba:
    enviar_mensaje_telegram("🧪 *PRUEBA DE ALERTA:* El centinela de granizo está conectado y vigilando CASA, CHACARITA, PALERMO, MICROCENTRO, MORÓN y LELOIR.")

    verificar_tiempo()
