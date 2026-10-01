import os
import requests
from shapely.geometry import Point, shape

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

LATITUD_OBJETIVO = -34.5950
LONGITUD_OBJETIVO = -58.6350

# URLs del SMN
URL_ACP = "https://ssl.smn.gob.ar/ws/index.php?resource=acp"
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


def obtener_datos_smn():
    # Cabeceras que emulan una sesión real de navegador para evitar el error 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.smn.gob.ar/",
        "Origin": "https://www.smn.gob.ar",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    }
    session = requests.Session()
    session.headers.update(headers)
    
    # Intento 1: recurso directo ACP
    try:
        res = session.get(URL_ACP, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Intento directo falló: {e}")

    # Intento 2: endpoint alternativo de alertas tempranas
    url_alt = "https://ssl.smn.gob.ar/ws/index.php?resource=warning"
    res = session.get(url_alt, timeout=15)
    res.raise_for_status()
    return res.json()


def verificar_granizo():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Variables de entorno de Telegram no configuradas.")
        return

    punto_usuario = Point(LONGITUD_OBJETIVO, LATITUD_OBJETIVO)
    alertas_previas = cargar_alertas_notificadas()

    try:
        datos = obtener_datos_smn()
    except Exception as e:
        print(f"Error al consultar el SMN: {e}")
        return

    features = datos.get("features", [])
    if not features:
        print("Sin avisos vigentes en el SMN.")
        return

    alertas_encontradas = 0

    for item in features:
        props = item.get("properties", {})
        geom = item.get("geometry", {})

        alerta_id = str(props.get("id", f"{props.get('date', '')}_{props.get('title', '')}"))

        if alerta_id in alertas_previas:
            continue

        try:
            poligono_tormenta = shape(geom)
        except Exception:
            continue

        if poligono_tormenta.contains(punto_usuario):
            alertas_encontradas += 1
            descripcion = props.get("description", "Aviso meteorológico vigente")
            validez = props.get("validez", "Próximas horas")
            tipo_alerta = props.get("title", "Alerta Meteorológica")

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
