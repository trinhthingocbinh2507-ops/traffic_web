from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
from datetime import datetime
import os
import threading

app = Flask(__name__)


# =========================================================
# MQTT
# =========================================================

MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")

TOPIC_STATUS = os.environ.get("TOPIC_STATUS", "traffic/status")
TOPIC_CONTROL = os.environ.get("TOPIC_CONTROL", "traffic/control")


# =========================================================
# DỮ LIỆU HIỆN TẠI
# =========================================================

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


# =========================================================
# LỊCH SỬ SỐ XE
# =========================================================

vehicle_history = []

MAX_HISTORY = 120


# =========================================================
# HÀM LƯU LỊCH SỬ
# =========================================================

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


# =========================================================
# MQTT CALLBACK
# =========================================================

def on_connect(client, userdata, flags, reason_code, properties):

    print("MQTT CALLBACK")
    print("REASON CODE:", reason_code)

    if reason_code == 0:

        print("MQTT: DA KET NOI")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)

        result = client.subscribe(TOPIC_STATUS)

        if result[0] == mqtt.MQTT_ERR_SUCCESS:
            print("MQTT: DA SUBSCRIBE", TOPIC_STATUS)
        else:
            print("MQTT: LOI SUBSCRIBE")


    else:

        print("MQTT: KET NOI THAT BAI")


# =========================================================
# NHẬN DỮ LIỆU TỪ ESP32
# =========================================================

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

        print("MQTT: LOI DOC DU LIEU:", e)


# =========================================================
# TẠO MQTT CLIENT
# =========================================================

# Dùng client_id riêng cho Render
CLIENT_ID = "flask_web_render"

mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID
)


mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


mqtt_client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


# =========================================================
# KẾT NỐI MQTT
# =========================================================

def ket_noi_mqtt():

    try:

        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        mqtt_client.loop_start()

        print("MQTT: DANG KHOI DONG...")

    except Exception as e:

        print("MQTT: KHONG KET NOI DUOC")
        print("LOI:", e)


# Kết nối ngay khi Render khởi động Flask
ket_noi_mqtt()


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# API: WEBSITE LẤY TRẠNG THÁI
# =========================================================

@app.route("/api/status")
def api_status():

    return jsonify(status_data)


# =========================================================
# API: WEBSITE LẤY LỊCH SỬ
# =========================================================

@app.route("/api/history")
def api_history():

    return jsonify(vehicle_history)


# =========================================================
# API: WEBSITE GỬI LỆNH
# =========================================================

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


        print("WEB GUI LENH:", command)


        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command
        )


        print("MQTT PUBLISH RC:", result.rc)


        if result.rc == mqtt.MQTT_ERR_SUCCESS:

            print("MQTT: DA PUBLISH", command)

            return jsonify({
                "success": True,
                "command": command
            })


        else:

            print("MQTT: PUBLISH THAT BAI")

            return jsonify({
                "success": False,
                "message": "MQTT publish loi"
            }), 500


    except Exception as e:

        print("API CONTROL LOI:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )