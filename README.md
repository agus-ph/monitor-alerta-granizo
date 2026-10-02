# ⛈️ Centinela de Granizo (Hail Alert Bot)

Sistema autónomo en la nube para el monitoreo meteorológico hiperlocal y la detección temprana de caída de granizo, con despacho inmediato de alertas críticas vía Telegram.

---

## 📌 Arquitectura del Sistema

[Cron-job.org]
│  (POST cada 5 min via webhook)
▼
[GitHub Actions] (Entorno de ejecución serverless)
│
├──> Consulta API Open-Meteo (WMO convective codes)
│      - Puntos: Casa, Morón, Leloir, Chacarita, Palermo, Microcentro, Villaguay
│
└──> ¿Riesgo de Granizo detectado?
├── SÍ: Despacho push a Telegram Bot API (con deduplicación)
└── NO: Finalización silenciosa

---

## 🚀 Características

* **Monitoreo Multizona:** Supervisión simultánea e independiente de múltiples coordenadas estratégicas:
  * Zona Oeste GBA: `CASA`, `MORON`, `LELOIR`.
  * CABA: `CHACARITA`, `PALERMO`, `MICROCENTRO`.
  * Entre Ríos: `VILLAGUAY`.
* **Detección Convectiva de Alta Resolución:** Evaluación de códigos meteorológicos WMO (96 y 99: tormentas con granizo) y tasas de precipitación convectiva a corto plazo (nowcasting).
* **Precisión de Reloj 24/7:** Disparado externamente cada 10 minutos mediante **Cron-job.org**, evitando las demoras de cola de los crons nativos de GitHub Actions.
* **Control de Duplicados (Deduplicación):** Persistencia de identificadores de evento (`alertas_enviadas.txt`) para prevenir spam de notificaciones durante una misma tormenta.
* **Costo Operativo Cero:** Construido sobre capas gratuitas permanentes (GitHub Actions público, Telegram Bot API, Open-Meteo API y Cron-job.org).

---

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python 3.11
* **Librerías principales:** `requests`, `shapely`
* **Datos Meteorológicos:** Open-Meteo API
* **Notificaciones:** Telegram Bot API
* **CI/CD & Orquestación:** GitHub Actions + Cron-job.org

---

## ⚙️ Configuración y Despliegue

### 1. Variables de Entorno (GitHub Secrets)

Para proteger las credenciales, el repositorio requiere dos secretos en **Settings > Secrets and variables > Actions**:

| Clave | Descripción |
| :--- | :--- |
| `TELEGRAM_TOKEN` | Token de autenticación provisto por `@BotFather`. |
| `TELEGRAM_CHAT_ID` | Identificador numérico del chat destinatario. |

### 2. Permisos de Flujo de Trabajo

Para permitir que el workflow registre el historial de alertas despachadas:
1. Ir a **Settings > Actions > General**.
2. En **Workflow permissions**, seleccionar **Read and write permissions**.
3. Guardar cambios.

### 3. Disparador Externo (Cron-job.org)

Para asegurar la ejecución puntual cada 10 minutos:
* **Método:** `POST`
* **URL:** `https://api.github.com/repos/<USUARIO>/<REPO>/actions/workflows/monitor.yml/dispatches`
* **Request Body:** `{"ref": "main"}`
* **Headers:**
  * `Authorization: Bearer <GITHUB_PERSONAL_ACCESS_TOKEN>`
  * `Accept: application/vnd.github.v3+json`
  * `Content-Type: application/json`
  * `User-Agent: cron-job-org`

---

## 📍 Modificación de Coordenadas

Para añadir o editar puntos de monitoreo, actualizar el diccionario `UBICACIONES` en `alerta_granizo.py`:

```python
UBICACIONES = {
    "CASA": {"lat": -34.6150, "lon": -58.6350},
    "MORON": {"lat": -34.6534, "lon": -58.6198},
    "LELOIR": {"lat": -34.6133, "lon": -58.6853},
    # Agregar nuevas ubicaciones aquí...
}
