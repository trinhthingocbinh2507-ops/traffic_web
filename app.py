from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
import threading
from datetime import datetime
import os
import uuid
import time
app = Flask(__name__)


# =========================================================
# MQTT
# =========================================================

MQTT_BROKER = os.environ.get("MQTT_BROKER")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))

MQTT_USERNAME = os.environ.get("MQTT_USERNAME")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")

TOPIC_STATUS = os.environ.get(
    "TOPIC_STATUS",
    "traffic/status"
)

TOPIC_CONTROL = os.environ.get(
    "TOPIC_CONTROL",
    "traffic/control"
)


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
# MQTT CALLBACK - KHI KẾT NỐI
# =========================================================

def on_connect(client, userdata, flags, reason_code, properties):

    print("================================")
    print("MQTT: DA KET NOI")
    print("MQTT CONNECT REASON:", reason_code)
    print("================================")

    result = client.subscribe(TOPIC_STATUS)

    print(
        "MQTT: DA SUBSCRIBE",
        TOPIC_STATUS,
        "RC:",
        result[0]
    )


# =========================================================
# MQTT CALLBACK - KHI MẤT KẾT NỐI
# =========================================================

def on_disconnect(client, userdata, flags, reason_code, properties):

    print("================================")
    print("MQTT: DA NGAT KET NOI")
    print("MQTT DISCONNECT REASON:", reason_code)
    print("================================")


# =========================================================
# NHẬN DỮ LIỆU TỪ ESP32
# =========================================================

def on_message(client, userdata, msg):

    global status_data

    try:

        payload = msg.payload.decode()

        print("MQTT STATUS:", payload)

        data = payload.split(",")

        # =================================================
        # ESP32 gửi:
        #
        # H1,H2,H3,H4,PHASE,TIME,
        # XANH1,VANG1,XANH2,VANG2
        # =================================================

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

            # Lưu lịch sử
            luu_lich_su()

    except Exception as e:

        print("MQTT: LOI DOC DU LIEU:", e)


# =========================================================
# TẠO MQTT CLIENT
# =========================================================

mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="flask_web_" + uuid.uuid4().hex[:8]
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

        # Gắn callback
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_message = on_message

        print()
        print("================================")
        print("MQTT: BAT DAU KET NOI...")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)
        print("USERNAME:", MQTT_USERNAME)
        print("================================")

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            10
        )

        print("MQTT: CONNECT() DA HOAN THANH")

        # Chạy MQTT network loop
        mqtt_client.loop_start()

        print("MQTT: DANG KHOI DONG...")

    except Exception as e:

        print("MQTT: KHONG KET NOI DUOC")
        print("LOI:", repr(e))


# =========================================================
# KHỞI ĐỘNG MQTT
# =========================================================

ket_noi_mqtt()


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# API: WEBSITE LẤY TRẠNG THÁI HIỆN TẠI
# =========================================================

@app.route("/api/status")
def api_status():

    return jsonify(status_data)


# =========================================================
# API: WEBSITE LẤY LỊCH SỬ SỐ XE
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


        # =================================================
        # KIỂM TRA TRẠNG THÁI MQTT
        # =================================================

        print()
        print("==============================")
        print("CHUAN BI GUI LENH:", command)
        print("==============================")

        print(
            "MQTT CONNECTED:",
            mqtt_client.is_connected()
        )


        # =================================================
        # GỬI LỆNH
        # =================================================

        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=1
        )


        print("PUBLISH RC:", result.rc)
        print("PUBLISH MID:", result.mid)


        # =================================================
        # KIỂM TRA KẾT QUẢ PUBLISH
        # =================================================

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            print("MQTT PUBLISH LOI")

            return jsonify({
                "success": False,
                "message": "MQTT publish loi",
                "rc": result.rc
            }), 500


        print("MQTT: DA GUI LENH:", command)


        return jsonify({
            "success": True,
            "command": command
        })


    except Exception as e:

        print("API CONTROL ERROR:", e)

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