import os
import requests
from shapely.geometry import Point, shape

# Credenciales inyectadas de forma segura desde GitHub Secrets
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Coordenadas a monitorear (Latitud, Longitud)
LATITUD_OBJETIVO = -34.5950
LONGITUD_OBJETIVO = -58.6350

SMN_ACP_URL = "https://ssl.smn.gob.ar/ws/index.php?resource=acp"
HISTORIAL_ALERTAS = "alertas_enviadas.txt"


def cargar_alertas_notificadas():
    if not os.path.exists(HISTORIAL_ALERTAS):
        return set()
    with open(HISTORIAL_ALERTAS, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def guardar_alerta_notificada(alerta_id):
    with open(HISTORIAL_ALERTAS, "a", encoding="utf-8") as f:
        f.write(f"{alerta_id}\n")


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
        print("-> Alerta despachada a Telegram.")
    except Exception as e:
        print(f"Error al enviar a Telegram: {e}")


def verificar_granizo():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Variables de entorno de Telegram no configuradas.")
        return

    punto_usuario = Point(LONGITUD_OBJETIVO, LATITUD_OBJETIVO)
    alertas_previas = cargar_alertas_notificadas()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MonitorGranizo/1.0"
    }

    try:
        res = requests.get(SMN_ACP_URL, headers=headers, timeout=15)
        res.raise_for_status()
        datos = res.json()
    except Exception as e:
        print(f"Error al consultar el SMN: {e}")
        return

    features = datos.get("features", [])
    if not features:
        print("Sin avisos a muy corto plazo vigentes en el país.")
        return

    alertas_encontradas = 0

    for item in features:
        props = item.get("properties", {})
        geom = item.get("geometry", {})

        alerta_id = str(
            props.get(
                "id", f"{props.get('date', '')}_{props.get('title', '')}"
            )
        )

        if alerta_id in alertas_previas:
            continue

        try:
            poligono_tormenta = shape(geom)
        except Exception:
            continue

        if poligono_tormenta.contains(punto_usuario):
            alertas_encontradas += 1
            descripcion = props.get("description", "Aviso meteorológico vigente")
            validez = props.get("validez", "Próximas 2-3 horas")
            tipo_alerta = props.get("title", "Aviso a Corto Plazo")

            texto_alerta = (
                "⚠️ *ALERTA METEOROLÓGICA EN TU ZONA*\n\n"
                f"📌 *Evento:* {tipo_alerta}\n"
                f"⏳ *Validez:* {validez}\n"
                f"📝 *Detalle:* {descripcion}\n\n"
                "🚗 *Revisá si tenés el auto bajo techo.*"
            )

            enviar_mensaje_telegram(texto_alerta)
            guardar_alerta_notificada(alerta_id)

    if alertas_encontradas == 0:
        print("Sin avisos activos para tu ubicación.")


if __name__ == "__main__":
    verificar_granizo()
