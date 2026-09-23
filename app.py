from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
from datetime import datetime
import os
import time
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
# TRẠNG THÁI MQTT
# =========================================================

mqtt_connected = False


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
# MQTT CALLBACK: CONNECT
# =========================================================

def on_connect(client, userdata, flags, reason_code, properties):

    global mqtt_connected

    print()
    print("========================================")
    print("MQTT CALLBACK")
    print("REASON CODE:", reason_code)
    print("========================================")

    if reason_code == 0:

        mqtt_connected = True

        print("MQTT: DA KET NOI")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)

        result, mid = client.subscribe(TOPIC_STATUS)

        if result == mqtt.MQTT_ERR_SUCCESS:

            print("MQTT: DA SUBSCRIBE", TOPIC_STATUS)

        else:

            print("MQTT: LOI SUBSCRIBE")
            print("MA LOI:", result)

    else:

        mqtt_connected = False

        print("MQTT: KET NOI THAT BAI")
        print("REASON CODE:", reason_code)


# =========================================================
# MQTT CALLBACK: DISCONNECT
# =========================================================

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):

    global mqtt_connected

    mqtt_connected = False

    print()
    print("========================================")
    print("MQTT: DA NGAT KET NOI")
    print("REASON CODE:", reason_code)
    print("========================================")


# =========================================================
# MQTT CALLBACK: MESSAGE
# =========================================================

def on_message(client, userdata, msg):

    global status_data

    try:

        payload = msg.payload.decode()

        print("MQTT STATUS:", payload)

        data = payload.split(",")

        # ESP32 gửi:
        #
        # H1,H2,H3,H4,PHASE,TIME,
        # XANH1,VANG1,XANH2,VANG2

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

# Dùng client ID riêng.
# Điều này tránh trường hợp app local và Render
# cùng sử dụng client_id = "flask_web".

CLIENT_ID = f"flask_web_{os.getpid()}"

print("========================================")
print("KHOI TAO MQTT")
print("========================================")
print("MQTT BROKER:", MQTT_BROKER)
print("MQTT PORT:", MQTT_PORT)
print("MQTT USER:", MQTT_USERNAME)
print("MQTT CLIENT ID:", CLIENT_ID)
print("========================================")


mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID
)


# Tài khoản HiveMQ
mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# TLS cho port 8883
mqtt_client.tls_set(
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)


# Gắn callback
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message


# =========================================================
# KẾT NỐI MQTT
# =========================================================

def ket_noi_mqtt():

    global mqtt_connected

    try:

        print()
        print("========================================")
        print("MQTT: DANG KHOI DONG...")
        print("========================================")

        print("MQTT: DANG CONNECT TO HIVEMQ...")

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        print("MQTT: CONNECT OK")

        # Bắt đầu vòng lặp MQTT
        mqtt_client.loop_start()

        print("MQTT: LOOP DA KHOI DONG")

        # Chờ callback on_connect
        for i in range(10):

            if mqtt_connected:

                break

            print(
                "MQTT: DANG CHO CONNECT...",
                i + 1,
                "/ 10"
            )

            time.sleep(1)

        print()

        if mqtt_connected:

            print("========================================")
            print("MQTT: KET NOI THANH CONG")
            print("========================================")

        else:

            print("========================================")
            print("MQTT: CHUA NHAN DUOC CONNECT CALLBACK")
            print("========================================")

    except Exception as e:

        mqtt_connected = False

        print()
        print("========================================")
        print("MQTT: KHONG KET NOI DUOC")
        print("========================================")

        print("LOI:", repr(e))

        print("========================================")


# Kết nối MQTT khi Flask khởi động
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

        command = data.get("command")

        if not command:

            return jsonify({
                "success": False,
                "message": "Thieu command"
            }), 400

        print()
        print("========================================")
        print("WEB GUI LENH:", command)
        print("MQTT CONNECTED:", mqtt_connected)
        print("========================================")

        # -------------------------------------------------
        # Kiểm tra MQTT
        # -------------------------------------------------

        if not mqtt_connected:

            print("MQTT: HIEN TAI KHONG KET NOI")

            return jsonify({
                "success": False,
                "message": "MQTT chua ket noi"
            }), 503

        # -------------------------------------------------
        # Gửi lệnh
        # -------------------------------------------------

        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=1
        )

        print("MQTT PUBLISH RC:", result.rc)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            print("MQTT: PUBLISH LOI")

            return jsonify({
                "success": False,
                "message": "MQTT publish loi"
            }), 500

        # Chờ MQTT xác nhận publish
        result.wait_for_publish(timeout=5)

        if result.is_published():

            print("MQTT: DA PUBLISH")
            print("TOPIC:", TOPIC_CONTROL)
            print("DATA:", command)

            return jsonify({
                "success": True,
                "command": command
            })

        else:

            print("MQTT: CHUA XAC NHAN PUBLISH")

            return jsonify({
                "success": False,
                "message": "MQTT chua xac nhan publish"
            }), 500

    except Exception as e:

        print()
        print("========================================")
        print("API CONTROL LOI")
        print("LOI:", repr(e))
        print("========================================")

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