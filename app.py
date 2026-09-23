from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
import threading
import time
import os

app = Flask(__name__)


# =========================================================
# MQTT - HIVEMQ
# =========================================================

MQTT_BROKER = "2111815ca2934f5bba664229abfd106b.s1.eu.hivemq.cloud"
MQTT_PORT = 8883

MQTT_USERNAME = "web_test"

# GIỮ MẬT KHẨU HIVEMQ CỦA BẠN Ở ĐÂY
MQTT_PASSWORD = "12345678"

TOPIC_STATUS = "traffic/status"
TOPIC_CONTROL = "traffic/control"


# =========================================================
# TRẠNG THÁI MQTT
# =========================================================

mqtt_connected = False
mqtt_lock = threading.Lock()


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
# LỊCH SỬ XE
# =========================================================

vehicle_history = []

MAX_HISTORY = 120


def luu_lich_su():

    try:

        from datetime import datetime

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
# MQTT CALLBACK - KẾT NỐI
# =========================================================

def on_connect(client, userdata, flags, reason_code, properties):

    global mqtt_connected

    print()
    print("======================================")
    print("MQTT CALLBACK")
    print("REASON CODE:", reason_code)
    print("======================================")

    if reason_code == 0:

        mqtt_connected = True

        print("MQTT: DA KET NOI")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)

        result, mid = client.subscribe(TOPIC_STATUS)

        if result == mqtt.MQTT_ERR_SUCCESS:

            print("MQTT: DA SUBSCRIBE", TOPIC_STATUS)

        else:

            print("MQTT: SUBSCRIBE THAT BAI")
            print("RC:", result)

    else:

        mqtt_connected = False

        print("MQTT: KET NOI THAT BAI")
        print("REASON CODE:", reason_code)


# =========================================================
# MQTT CALLBACK - MẤT KẾT NỐI
# =========================================================

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):

    global mqtt_connected

    mqtt_connected = False

    print()
    print("======================================")
    print("MQTT: BI NGAT KET NOI")
    print("REASON CODE:", reason_code)
    print("======================================")


# =========================================================
# MQTT CALLBACK - NHẬN STATUS TỪ ESP32
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

# Tạo client ID riêng cho worker hiện tại
worker_id = os.getpid()

MQTT_CLIENT_ID = f"traffic_web_{worker_id}"

print()
print("======================================")
print("TAO MQTT CLIENT")
print("CLIENT ID:", MQTT_CLIENT_ID)
print("======================================")


mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=MQTT_CLIENT_ID
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


# =========================================================
# THREAD MQTT
# =========================================================

def mqtt_worker():

    global mqtt_connected

    print()
    print("======================================")
    print("MQTT WORKER BAT DAU")
    print("======================================")


    while True:

        try:

            if not mqtt_client.is_connected():

                mqtt_connected = False

                print()
                print("MQTT: DANG KET NOI...")
                print("BROKER:", MQTT_BROKER)
                print("PORT:", MQTT_PORT)
                print("USERNAME:", MQTT_USERNAME)

                try:

                    mqtt_client.connect(
                        MQTT_BROKER,
                        MQTT_PORT,
                        60
                    )

                    print("MQTT: CONNECT() THANH CONG")

                except Exception as e:

                    print("MQTT: CONNECT() LOI")
                    print("LOI:", e)

                    time.sleep(5)

                    continue


            # Quan trọng:
            # loop_forever() xử lý CONNACK,
            # callback on_connect và message MQTT.

            mqtt_client.loop(
                timeout=1.0
            )


        except Exception as e:

            mqtt_connected = False

            print("MQTT WORKER LOI:", e)

            time.sleep(5)


# =========================================================
# KHỞI ĐỘNG MQTT THREAD
# =========================================================

mqtt_thread = threading.Thread(
    target=mqtt_worker,
    daemon=True
)

mqtt_thread.start()


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# API STATUS
# =========================================================

@app.route("/api/status")
def api_status():

    return jsonify(status_data)


# =========================================================
# API HISTORY
# =========================================================

@app.route("/api/history")
def api_history():

    return jsonify(vehicle_history)


# =========================================================
# API MQTT STATUS
# =========================================================

@app.route("/api/mqtt-status")
def api_mqtt_status():

    return jsonify({
        "connected": mqtt_connected,
        "client_id": MQTT_CLIENT_ID,
        "broker": MQTT_BROKER,
        "port": MQTT_PORT
    })


# =========================================================
# API TEST TCP
# =========================================================

@app.route("/test-mqtt")
def test_mqtt():

    import socket

    try:

        sock = socket.create_connection(
            (MQTT_BROKER, MQTT_PORT),
            timeout=5
        )

        sock.close()

        return jsonify({
            "success": True,
            "message": "Render ket noi duoc den MQTT broker",
            "broker": MQTT_BROKER,
            "port": MQTT_PORT
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e),
            "broker": MQTT_BROKER,
            "port": MQTT_PORT
        }), 500


# =========================================================
# API GỬI LỆNH ĐIỀU KHIỂN
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


        # Kiểm tra MQTT đã thực sự kết nối chưa

        if not mqtt_connected or not mqtt_client.is_connected():

            print()
            print("MQTT: KHONG THE GUI LENH")
            print("MQTT CHUA KET NOI")
            print("COMMAND:", command)

            return jsonify({
                "success": False,
                "message": "MQTT chua ket noi"
            }), 503


        print()
        print("======================================")
        print("WEB GUI LENH:", command)
        print("TOPIC:", TOPIC_CONTROL)
        print("======================================")


        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=0,
            retain=False
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
                "message": "MQTT publish loi",
                "rc": result.rc
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