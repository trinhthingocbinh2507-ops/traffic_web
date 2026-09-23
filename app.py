from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
import threading
from datetime import datetime
import os
import time

app = Flask(__name__)

# ==========================================
# MQTT CONFIG
# ==========================================

MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")

TOPIC_STATUS = os.environ.get("TOPIC_STATUS", "traffic/status")
TOPIC_CONTROL = os.environ.get("TOPIC_CONTROL", "traffic/control")

# ==========================================
# DATA
# ==========================================

status_data = {
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

vehicle_history = []
MAX_HISTORY = 120

mqtt_connected = False


# ==========================================
# LUU LICH SU
# ==========================================

def luu_lich_su():
    try:
        now = datetime.now().strftime("%H:%M:%S")

        item = {
            "time": now,
            "h1": status_data["h1"],
            "h2": status_data["h2"],
            "h3": status_data["h3"],
            "h4": status_data["h4"]
        }

        vehicle_history.append(item)

        if len(vehicle_history) > MAX_HISTORY:
            vehicle_history.pop(0)

    except Exception as e:
        print("LOI LUU LICH SU:", e)


# ==========================================
# MQTT CALLBACK
# ==========================================

def on_connect(client, userdata, flags, reason_code, properties):

    global mqtt_connected

    print("======================================")
    print("MQTT CALLBACK ON_CONNECT")
    print("MQTT REASON CODE:", reason_code)
    print("======================================")

    if reason_code == 0:

        mqtt_connected = True

        print("MQTT: DA KET NOI")
        print("MQTT BROKER:", MQTT_BROKER)
        print("MQTT PORT:", MQTT_PORT)

        result = client.subscribe(TOPIC_STATUS)

        if result[0] == mqtt.MQTT_ERR_SUCCESS:
            print("MQTT: DA SUBSCRIBE", TOPIC_STATUS)
        else:
            print("MQTT: LOI SUBSCRIBE")
            print("MA LOI:", result[0])

    else:

        mqtt_connected = False

        print("MQTT: KET NOI THAT BAI")
        print("REASON CODE:", reason_code)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):

    global mqtt_connected

    mqtt_connected = False

    print("======================================")
    print("MQTT: DA NGAT KET NOI")
    print("REASON CODE:", reason_code)
    print("======================================")


def on_message(client, userdata, msg):

    global status_data

    try:

        payload = msg.payload.decode()

        print("MQTT STATUS:", payload)

        data = payload.split(",")

        if len(data) >= 10:

            status_data["h1"] = int(data[0])
            status_data["h2"] = int(data[1])
            status_data["h3"] = int(data[2])
            status_data["h4"] = int(data[3])

            status_data["phase"] = data[4]
            status_data["time"] = int(data[5])

            status_data["xanh1"] = int(data[6])
            status_data["vang1"] = int(data[7])

            status_data["xanh2"] = int(data[8])
            status_data["vang2"] = int(data[9])

            luu_lich_su()

    except Exception as e:

        print("MQTT: LOI DOC DU LIEU:")
        print(e)


# ==========================================
# TAO MQTT CLIENT
# ==========================================

print("======================================")
print("KHOI TAO MQTT")
print("======================================")

print("MQTT BROKER:", MQTT_BROKER)
print("MQTT PORT:", MQTT_PORT)
print("MQTT USER:", MQTT_USERNAME)

mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"flask_web_{os.getpid()}"
)

mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

mqtt_client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message


# ==========================================
# KET NOI MQTT
# ==========================================

def ket_noi_mqtt():

    global mqtt_connected

    print("======================================")
    print("MQTT: DANG KHOI DONG...")
    print("======================================")

    try:

        print("MQTT: DANG CONNECT TO BROKER...")

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        print("MQTT: LENH CONNECT DA DUOC GUI")

        mqtt_client.loop_start()

        print("MQTT: LOOP DA KHOI DONG")

        # Cho callback on_connect
        for i in range(10):

            if mqtt_connected:
                break

            print(
                "MQTT: DANG CHO CONNECT...",
                i + 1,
                "/ 10"
            )

            time.sleep(1)

        if mqtt_connected:

            print("======================================")
            print("MQTT: KET NOI THANH CONG")
            print("======================================")

        else:

            print("======================================")
            print("MQTT: CHUA NHAN DUOC CALLBACK CONNECT")
            print("======================================")

    except Exception as e:

        mqtt_connected = False

        print("======================================")
        print("MQTT: KHONG KET NOI DUOC")
        print("LOI:", repr(e))
        print("======================================")


# ==========================================
# KHOI DONG MQTT NGAY KHI APP CHAY
# ==========================================

ket_noi_mqtt()


# ==========================================
# WEB ROUTES
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


@app.route("/api/status")
def api_status():

    return jsonify(status_data)


@app.route("/api/history")
def api_history():

    return jsonify(vehicle_history)


# ==========================================
# GUI LENH DIEU KHIEN
# ==========================================

@app.route("/api/control", methods=["POST"])
def api_control():

    try:

        data = request.get_json()

        command = data.get("command")

        if not command:

            return jsonify({
                "success": False,
                "message": "Thieu command"
            }), 400

        print("======================================")
        print("WEB GUI LENH:", command)
        print("MQTT CONNECTED:", mqtt_connected)
        print("======================================")

        # ------------------------------
        # KIEM TRA MQTT
        # ------------------------------

        if not mqtt_connected:

            print("MQTT: KHONG DANG KET NOI")

            return jsonify({
                "success": False,
                "message": "MQTT chua ket noi"
            }), 503

        # ------------------------------
        # PUBLISH
        # ------------------------------

        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=1
        )

        print("MQTT PUBLISH RC:", result.rc)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            print("MQTT: PUBLISH THAT BAI")

            return jsonify({
                "success": False,
                "message": f"MQTT publish loi: {result.rc}"
            }), 500

        # ------------------------------
        # CHO MQTT XAC NHAN
        # ------------------------------

        result.wait_for_publish(timeout=5)

        if result.is_published():

            print("======================================")
            print("MQTT: DA PUBLISH THANH CONG")
            print("TOPIC:", TOPIC_CONTROL)
            print("DATA:", command)
            print("======================================")

            return jsonify({
                "success": True,
                "command": command
            })

        else:

            print("======================================")
            print("MQTT: PUBLISH CHUA DUOC XAC NHAN")
            print("======================================")

            return jsonify({
                "success": False,
                "message": "MQTT chua xac nhan publish"
            }), 500

    except Exception as e:

        print("======================================")
        print("API CONTROL LOI")
        print("LOI:", repr(e))
        print("======================================")

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )