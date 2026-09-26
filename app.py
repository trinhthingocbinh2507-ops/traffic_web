from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
import os
import json
import threading
import time
import uuid
from datetime import datetime

app = Flask(__name__)

# =========================================================
# MQTT
# =========================================================
MQTT_BROKER = os.environ.get(
    "MQTT_BROKER",
    "2111815ca2934f5bba664229abfd106b.s1.eu.hivemq.cloud"
)
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "web_test")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")

TOPIC_STATUS = os.environ.get("TOPIC_STATUS", "traffic/status")
TOPIC_CONTROL = os.environ.get("TOPIC_CONTROL", "traffic/control")

# =========================================================
# STATUS
# =========================================================
STATUS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "status_data.json"
)
status_lock = threading.Lock()

DEFAULT_STATUS = {
    "h1": 0,
    "h2": 0,
    "h3": 0,
    "h4": 0,
    "phase": "ALL_RED",
    "time": 0,
    "xanh1": 15,
    "vang1": 3,
    "xanh2": 15,
    "vang2": 3
}


def doc_status():
    with status_lock:
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print("LOI DOC STATUS:", repr(e))
        return DEFAULT_STATUS.copy()


def luu_status(data):
    with status_lock:
        try:
            with open(STATUS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print("LOI LUU STATUS:", repr(e))


if not os.path.exists(STATUS_FILE):
    luu_status(DEFAULT_STATUS.copy())

# =========================================================
# LICH SU XE
# =========================================================
vehicle_history = []
MAX_HISTORY = 120


def luu_lich_su(status):
    try:
        vehicle_history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "h1": status["h1"],
            "h2": status["h2"],
            "h3": status["h3"],
            "h4": status["h4"]
        })

        if len(vehicle_history) > MAX_HISTORY:
            vehicle_history.pop(0)
    except Exception as e:
        print("LOI LUU LICH SU:", repr(e))

# =========================================================
# MQTT CALLBACKS
# =========================================================
def on_connect(client, userdata, flags, reason_code, properties):
    print("MQTT: DA KET NOI")
    print("MQTT CONNECT REASON:", reason_code)
    print("MQTT CONNECTED:", client.is_connected())

    result = client.subscribe(TOPIC_STATUS, qos=1)

    if result[0] == mqtt.MQTT_ERR_SUCCESS:
        print("MQTT: DA SUBSCRIBE", TOPIC_STATUS)
    else:
        print("MQTT: LOI SUBSCRIBE RC:", result[0])


def on_disconnect(client, userdata, flags, reason_code, properties):
    print("MQTT: DA NGAT KET NOI")
    print("MQTT DISCONNECT REASON:", reason_code)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        print("MQTT NHAN:", msg.topic, "->", payload)

        if msg.topic != TOPIC_STATUS:
            return

        data = payload.split(",")

        # H1,H2,H3,H4,PHASE,TIME,XANH1,VANG1,XANH2,VANG2
        if len(data) < 10:
            print("MQTT STATUS: DU LIEU KHONG DU 10 TRUONG")
            return

        status = {
            "h1": int(data[0]),
            "h2": int(data[1]),
            "h3": int(data[2]),
            "h4": int(data[3]),
            "phase": data[4],
            "time": int(data[5]),
            "xanh1": int(data[6]),
            "vang1": int(data[7]),
            "xanh2": int(data[8]),
            "vang2": int(data[9])
        }

        luu_status(status)
        luu_lich_su(status)
        print("STATUS DA LUU:", status)

    except Exception as e:
        print("MQTT: LOI DOC STATUS:", repr(e))

# =========================================================
# MQTT CLIENT
# =========================================================
mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="flask_status_" + uuid.uuid4().hex[:8],
    protocol=mqtt.MQTTv311
)

mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message


def ket_noi_mqtt():
    try:
        print("MQTT: BAT DAU KET NOI...")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)
        print("USERNAME:", MQTT_USERNAME)

        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()

        for i in range(15):
            if mqtt_client.is_connected():
                print("MQTT: KET NOI THANH CONG")
                return True
            time.sleep(1)
            print("MQTT: DANG CHO...", i + 1, "/ 15")

        print("MQTT: KHONG KET NOI DUOC")
        return False

    except Exception as e:
        print("MQTT: LOI KET NOI:", repr(e))
        return False


# Quan trong: phai goi khi Gunicorn import app.py
ket_noi_mqtt()

# =========================================================
# WEB
# =========================================================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(doc_status())


@app.route("/api/history")
def api_history():
    return jsonify(vehicle_history)


# =========================================================
# WEB -> ESP32
# =========================================================
@app.route("/api/control", methods=["POST"])
def api_control():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "message": "Khong co du lieu JSON"
            }), 400

        command = data.get("command")

        if not command:
            return jsonify({
                "success": False,
                "message": "Thieu command"
            }), 400

        print("CHUAN BI GUI LENH:", command)
        print("MQTT CONNECTED:", mqtt_client.is_connected())

        if not mqtt_client.is_connected():
            return jsonify({
                "success": False,
                "message": "MQTT chua ket noi"
            }), 503

        # QoS 0 de API phan hoi nhanh.
        # Khong dung wait_for_publish().
        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=0,
            retain=False
        )

        print("CONTROL PUBLISH RC:", result.rc)
        print("CONTROL PUBLISH MID:", result.mid)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            return jsonify({
                "success": False,
                "message": "MQTT publish loi",
                "rc": result.rc
            }), 500

        print("MQTT CONTROL: DA GUI LENH:", command)

        return jsonify({
            "success": True,
            "command": command
        })

    except Exception as e:
        print("API CONTROL ERROR:", repr(e))
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# LOCAL
# =========================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )
