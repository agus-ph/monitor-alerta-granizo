import os
import json
import time
import requests

# Credenciales de Telegram (desde Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Tiempo de espera mínimo entre alertas de la misma zona (en segundos)
# 2 horas = 2 * 60 * 60 = 7200 segundos
TIEMPO_COOLDOWN_SEGUNDOS = 7200

# Archivo donde guardamos cuándo fue la última alerta por zona
HISTORIAL_ALERTAS = "registro_alertas.json"

UBICACIONES = {
    "CASA": {"lat": -34.6150, "lon": -58.6350},
    "MORON": {"lat": -34.6534, "lon": -58.6198},
    "LELOIR": {"lat": -34.6133, "lon": -58.6853},
    "CHACARITA": {"lat": -34.5875, "lon": -58.4550},
    "PALERMO": {"lat": -34.5780, "lon": -58.4265},
    "MICROCENTRO": {"lat": -34.6037, "lon": -58.3750},
    "VILLAGUAY": {"lat": -31.8653, "lon": -59.0270},
}


def cargar_historial():
    """Carga los timestamps de las últimas alertas enviadas."""
    if not os.path.exists(HISTORIAL_ALERTAS):
        return {}
    try:
        with open(HISTORIAL_ALERTAS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_historial(historial):
    """Persiste los timestamps actualizados en disco."""
    try:
        with open(HISTORIAL_ALERTAS, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=2)
    except Exception as e:
        print(f"Error guardando historial: {e}")


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
        return True
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")
        return False


def evaluar_zona(nombre_zona, coords, historial):
    ahora = time.time()
    ultimo_envio = historial.get(nombre_zona, 0)

    # Si ya se envió una alerta para esta zona hace menos de 2 horas, saltear
    if ahora - ultimo_envio < TIEMPO_COOLDOWN_SEGUNDOS:
        minutos_restantes = int((TIEMPO_COOLDOWN_SEGUNDOS - (ahora - ultimo_envio)) / 60)
        print(f"[{nombre_zona}] En período de espera (silencio activo por {minutos_restantes} min más).")
        return False

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
        return False

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    current_code = current.get("weather_code", 0)
    hourly_codes = hourly.get("weather_code", [])
    hourly_times = hourly.get("time", [])

    amenaza_granizo = False
    motivo = ""

    # Códigos WMO de tormenta con granizo:
    # 96: Tormenta con granizo leve/moderado
    # 99: Tormenta severa con granizo fuerte
    # 95: Tormenta eléctrica severa
    if current_code in [96, 99]:
        amenaza_granizo = True
        motivo = "Tormenta con caída de granizo en curso o inminente."
    elif current_code == 95 and current.get("precipitation", 0) > 10.0:
        amenaza_granizo = True
        motivo = "Tormenta eléctrica severa con alta probabilidad de granizo."

    if not amenaza_granizo and hourly_codes:
        for t, code in zip(hourly_times, hourly_codes):
            if code in [96, 99]:
                amenaza_granizo = True
                hora = t.split("T")[-1]
                motivo = f"Pronóstico de tormenta con granizo estimado a las {hora} hs."
                break

    if amenaza_granizo:
        mensaje = (
            f"⚠️ *ALERTA DE GRANIZO: {nombre_zona}*\n\n"
            f"📍 *Zona afectada:* {nombre_zona}\n"
            f"📌 *Diagnóstico:* {motivo}\n\n"
            "🚗 *Revisá si el auto está bajo techo en esa zona.*"
        )
        if enviar_mensaje_telegram(mensaje):
            historial[nombre_zona] = ahora
            return True
    else:
        print(f"[{nombre_zona}] Estable (código {current_code}). Sin riesgo.")

    return False


def verificar_tiempo():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Variables de entorno ausentes.")
        return

    historial = cargar_historial()
    hubo_cambios = False

    for zona, coords in UBICACIONES.items():
        alerta_enviada = evaluar_zona(zona, coords, historial)
        if alerta_enviada:
            hubo_cambios = True

    if hubo_cambios:
        guardar_historial(historial)


if __name__ == "__main__":
    verificar_tiempo()
