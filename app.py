from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import ssl
import os
import json
import threading
from datetime import datetime

app = Flask(__name__)


# =========================================================
# MQTT
# =========================================================

MQTT_BROKER = os.environ.get(
    "MQTT_BROKER",
    "2111815ca2934f5bba664229abfd106b.s1.eu.hivemq.cloud"
)

MQTT_PORT = int(
    os.environ.get("MQTT_PORT", 8883)
)

MQTT_USERNAME = os.environ.get(
    "MQTT_USERNAME",
    "web_test"
)

MQTT_PASSWORD = os.environ.get(
    "MQTT_PASSWORD"
)

TOPIC_STATUS = os.environ.get(
    "TOPIC_STATUS",
    "traffic/status"
)

TOPIC_CONTROL = os.environ.get(
    "TOPIC_CONTROL",
    "traffic/control"
)


# =========================================================
# FILE LƯU TRẠNG THÁI
# =========================================================

STATUS_FILE = "status_data.json"

status_lock = threading.Lock()


# =========================================================
# TRẠNG THÁI MẶC ĐỊNH
# =========================================================

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


# =========================================================
# ĐỌC TRẠNG THÁI TỪ FILE
# =========================================================

def doc_status():

    with status_lock:

        try:

            if os.path.exists(STATUS_FILE):

                with open(
                    STATUS_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(file)

                return data

        except Exception as e:

            print("LOI DOC STATUS FILE:", e)

        return DEFAULT_STATUS.copy()


# =========================================================
# LƯU TRẠNG THÁI RA FILE
# =========================================================

def luu_status(data):

    with status_lock:

        try:

            with open(
                STATUS_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    ensure_ascii=False
                )

        except Exception as e:

            print("LOI LUU STATUS FILE:", e)


# =========================================================
# KHỞI TẠO STATUS
# =========================================================

if not os.path.exists(STATUS_FILE):

    luu_status(DEFAULT_STATUS.copy())


# =========================================================
# LỊCH SỬ XE
# =========================================================

vehicle_history = []

MAX_HISTORY = 120


# =========================================================
# LƯU LỊCH SỬ
# =========================================================

def luu_lich_su(status):

    try:

        now = datetime.now().strftime("%H:%M:%S")

        item = {

            "time": now,

            "h1": status["h1"],
            "h2": status["h2"],
            "h3": status["h3"],
            "h4": status["h4"]

        }

        vehicle_history.append(item)

        if len(vehicle_history) > MAX_HISTORY:

            vehicle_history.pop(0)

    except Exception as e:

        print("LOI LUU LICH SU:", e)


# =========================================================
# MQTT CONNECT
# =========================================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    print("MQTT: DA KET NOI")

    result = client.subscribe(
        TOPIC_STATUS
    )

    if result[0] == mqtt.MQTT_ERR_SUCCESS:

        print(
            "MQTT: DA SUBSCRIBE",
            TOPIC_STATUS
        )

    else:

        print(
            "MQTT: LOI SUBSCRIBE",
            TOPIC_STATUS
        )


# =========================================================
# MQTT NHẬN STATUS TỪ ESP32
# =========================================================

def on_message(
    client,
    userdata,
    msg
):

    try:

        payload = msg.payload.decode()

        print(
            "MQTT STATUS:",
            payload
        )

        data = payload.split(",")

        # =================================================
        # ESP32 GỬI:
        #
        # H1,H2,H3,H4,PHASE,TIME,
        # XANH1,VANG1,XANH2,VANG2
        # =================================================

        if len(data) >= 10:

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

            # =============================================
            # LƯU TRẠNG THÁI
            # =============================================

            luu_status(status)

            # =============================================
            # LƯU LỊCH SỬ
            # =============================================

            luu_lich_su(status)

            print(
                "STATUS DA LUU:",
                status
            )

    except Exception as e:

        print(
            "MQTT: LOI DOC DU LIEU:",
            e
        )


# =========================================================
# TẠO MQTT CLIENT
# =========================================================

mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="flask_web"
)


# =========================================================
# MQTT USERNAME + PASSWORD
# =========================================================

mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)


# =========================================================
# MQTT TLS
# =========================================================

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

        print(
            "MQTT: BAT DAU KET NOI..."
        )

        print(
            "BROKER:",
            MQTT_BROKER
        )

        print(
            "PORT:",
            MQTT_PORT
        )

        print(
            "USERNAME:",
            MQTT_USERNAME
        )

        mqtt_client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        print(
            "MQTT: CONNECT() DA HOAN THANH"
        )

        mqtt_client.loop_start()

        print(
            "MQTT: DANG KHOI DONG..."
        )

    except Exception as e:

        print(
            "MQTT: KHONG KET NOI DUOC"
        )

        print(
            "LOI:",
            e
        )


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# API STATUS
# =========================================================

@app.route("/api/status")
def api_status():

    # ĐỌC TRỰC TIẾP STATUS MỚI NHẤT
    status = doc_status()

    return jsonify(status)


# =========================================================
# API HISTORY
# =========================================================

@app.route("/api/history")
def api_history():

    return jsonify(
        vehicle_history
    )


# =========================================================
# API CONTROL
# =========================================================

@app.route(
    "/api/control",
    methods=["POST"]
)
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


        print("======================================")
        print("CHUAN BI GUI MQTT")
        print("TOPIC :", TOPIC_CONTROL)
        print("COMMAND:", command)
        print("CONNECTED:", mqtt_client.is_connected())
        print("======================================")


        # =================================================
        # KIỂM TRA MQTT CÓ ĐANG KẾT NỐI KHÔNG
        # =================================================

        if not mqtt_client.is_connected():

            print("MQTT: CLIENT KHONG KET NOI")

            return jsonify({
                "success": False,
                "message": "Flask chua ket noi MQTT broker"
            }), 500


        # =================================================
        # PUBLISH
        # =================================================

        result = mqtt_client.publish(
            TOPIC_CONTROL,
            command,
            qos=1,
            retain=False
        )


        print(
            "MQTT PUBLISH RC:",
            result.rc
        )


        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            print(
                "MQTT PUBLISH LOI:",
                result.rc
            )

            return jsonify({
                "success": False,
                "message": "MQTT publish loi",
                "rc": result.rc
            }), 500


        # =================================================
        # CHỜ MESSAGE ĐƯỢC GỬI THỰC SỰ
        # =================================================

        result.wait_for_publish(
            timeout=5
        )


        # =================================================
        # KIỂM TRA ĐÃ PUBLISH XONG
        # =================================================

        if not result.is_published():

            print(
                "MQTT: KHONG XAC NHAN DUOC PUBLISH"
            )

            return jsonify({
                "success": False,
                "message": "MQTT chua xac nhan publish"
            }), 500


        # =================================================
        # THÀNH CÔNG
        # =================================================

        print(
            "GUI LENH THANH CONG:",
            command
        )

        return jsonify({

            "success": True,

            "command": command,

            "topic": TOPIC_CONTROL

        })


    except Exception as e:

        print(
            "API CONTROL LOI:",
            e
        )

        return jsonify({

            "success": False,

            "message": str(e)

        }), 500


# =========================================================
# KHỞI ĐỘNG MQTT
#
# QUAN TRỌNG:
# Gọi ở ngoài if __name__ == "__main__"
# để Gunicorn trên Render cũng kết nối MQTT.
# =========================================================

ket_noi_mqtt()


# =========================================================
# CHẠY LOCAL
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True,

        use_reloader=False

    )