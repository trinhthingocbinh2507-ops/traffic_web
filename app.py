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

STATUS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "status_data.json"
)

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

            print(
                "LOI DOC STATUS FILE:",
                repr(e)
            )

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

            print(
                "LOI LUU STATUS FILE:",
                repr(e)
            )


# =========================================================
# KHỞI TẠO STATUS
# =========================================================

if not os.path.exists(STATUS_FILE):

    luu_status(
        DEFAULT_STATUS.copy()
    )


# =========================================================
# LỊCH SỬ XE
# =========================================================

vehicle_history = []

MAX_HISTORY = 120

# =========================================================
# BIẾN DEBUG MQTT
# Dùng để xác nhận Render -> HiveMQ -> Render.
# Không ảnh hưởng đường điều khiển traffic/control.
# =========================================================

mqtt_test_event = threading.Event()
mqtt_test_lock = threading.Lock()
mqtt_test_last_payload = ""
mqtt_test_last_topic = ""


# =========================================================
# LƯU LỊCH SỬ
# =========================================================

def luu_lich_su(status):

    try:

        now = datetime.now().strftime(
            "%H:%M:%S"
        )

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

        print(
            "LOI LUU LICH SU:",
            repr(e)
        )


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

    print()
    print("================================")
    print("MQTT: DA KET NOI")
    print("MQTT CONNECT REASON:", reason_code)
    print("MQTT CONNECT FLAGS:", flags)
    print("MQTT PROTOCOL:", client._protocol)
    print("MQTT CONNECTED:", client.is_connected())
    print("================================")

    result = client.subscribe(
        TOPIC_STATUS,
        qos=1
    )

    if result[0] == mqtt.MQTT_ERR_SUCCESS:

        print(
            "MQTT: DA SUBSCRIBE",
            TOPIC_STATUS
        )

        print(
            "SUBSCRIBE MID:",
            result[1]
        )

    else:

        print(
            "MQTT: LOI SUBSCRIBE",
            TOPIC_STATUS,
            "RC:",
            result[0]
        )


# =========================================================
# MQTT DISCONNECT
# =========================================================

def on_disconnect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    print()
    print("================================")
    print("MQTT: DA NGAT KET NOI")
    print("MQTT DISCONNECT REASON:", reason_code)
    print("MQTT DISCONNECT FLAGS:", flags)
    print("MQTT CONNECTED:", client.is_connected())
    print("================================")


# =========================================================
# MQTT PUBLISH ACK
# =========================================================

def on_publish(
    client,
    userdata,
    mid,
    reason_code,
    properties
):

    print()
    print("================================")
    print("MQTT: BROKER DA XAC NHAN PUBLISH")
    print("PUBLISH MID:", mid)
    print("PUBLISH REASON:", reason_code)
    print("================================")


# =========================================================
# MQTT LOG CHI TIẾT
# =========================================================

def on_log(
    client,
    userdata,
    level,
    buf
):

    print(
        "MQTT LOG:",
        buf
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
            "MQTT NHAN MESSAGE:",
            msg.topic,
            "->",
            payload
        )

        # =================================================
        # MESSAGE DEBUG TỪ TRAFFIC/TEST
        # Render subscribe topic test rồi tự publish.
        # Nếu nhận lại message thì broker đã nhận và chuyển tiếp.
        # =================================================

        if msg.topic == "traffic/test":

            global mqtt_test_last_payload
            global mqtt_test_last_topic

            with mqtt_test_lock:
                mqtt_test_last_payload = payload
                mqtt_test_last_topic = msg.topic

            mqtt_test_event.set()

            print(
                "MQTT TEST: DA NHAN LAI TU BROKER"
            )

            return

        if msg.topic != TOPIC_STATUS:
            print(
                "MQTT: BO QUA TOPIC KHONG PHAN LOAI:",
                msg.topic
            )
            return

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

        else:

            print(
                "MQTT STATUS: DU LIEU KHONG DU 10 TRUONG"
            )

    except Exception as e:

        print(
            "MQTT: LOI DOC DU LIEU:",
            repr(e)
        )


# =========================================================
# TẠO MQTT CLIENT
#
# DÙNG MQTT 3.1.1
# ĐÚNG THEO CODE CŨ CỦA BẠN
# =========================================================

mqtt_client = mqtt.Client(

    mqtt.CallbackAPIVersion.VERSION2,

    client_id=(
        "flask_status_"
        + uuid.uuid4().hex[:8]
    ),

    protocol=mqtt.MQTTv311
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
# GẮN CALLBACK MQTT
# =========================================================

mqtt_client.on_connect = on_connect

mqtt_client.on_disconnect = on_disconnect

mqtt_client.on_message = on_message

mqtt_client.on_publish = on_publish

mqtt_client.on_log = on_log


# =========================================================
# KẾT NỐI MQTT
# =========================================================

def ket_noi_mqtt():

    try:

        print()
        print("================================")
        print("MQTT: BAT DAU KET NOI...")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)
        print("USERNAME:", MQTT_USERNAME)
        print(
            "CLIENT ID:",
            mqtt_client._client_id.decode()
        )
        print(
            "PROTOCOL:",
            mqtt_client._protocol
        )
        print("================================")

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
            "MQTT: DANG CHO XAC NHAN KET NOI..."
        )

        # =================================================
        # CHỜ MQTT CONNECT THỰC SỰ
        # =================================================

        for i in range(15):

            if mqtt_client.is_connected():

                print()
                print("================================")
                print("MQTT: KET NOI THANH CONG")
                print("MQTT CONNECTED = True")
                print("================================")

                return True

            time.sleep(1)

            print(
                "MQTT: DANG CHO...",
                i + 1,
                "/ 15"
            )

        print()
        print("================================")
        print("MQTT: KHONG KET NOI DUOC")
        print(
            "MQTT CONNECTED =",
            mqtt_client.is_connected()
        )
        print("================================")

        return False

    except Exception as e:

        print()
        print("================================")
        print("MQTT: LOI KET NOI")
        print(
            "LOI:",
            repr(e)
        )
        print("================================")

        return False


# =========================================================
# KHỞI ĐỘNG MQTT
#
# QUAN TRỌNG:
# Gọi ngoài if __name__ == "__main__"
# để Gunicorn trên Render cũng kết nối MQTT.
# =========================================================

ket_noi_mqtt()


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
# API TEST MQTT
#
# DÙNG RIÊNG ĐỂ DEBUG
#
# QoS 1:
# Nếu HiveMQ nhận PUBLISH và gửi PUBACK
# thì on_publish() sẽ được gọi.
#
# KHÔNG dùng endpoint này cho điều khiển thực tế.
# =========================================================

@app.route(
    "/api/test-mqtt",
    methods=["GET"]
)
def test_mqtt():

    try:

        print()
        print("================================")
        print("MQTT TEST BAT DAU")
        print("================================")

        print(
            "MQTT CONNECTED:",
            mqtt_client.is_connected()
        )

        if not mqtt_client.is_connected():

            print(
                "MQTT TEST: CHUA KET NOI"
            )

            return jsonify({
                "success": False,
                "message": "MQTT chua ket noi"
            }), 503

        # =================================================
        # XOA KET QUA TEST CU
        # =================================================

        mqtt_test_event.clear()

        global mqtt_test_last_payload
        global mqtt_test_last_topic

        with mqtt_test_lock:
            mqtt_test_last_payload = ""
            mqtt_test_last_topic = ""

        # =================================================
        # SUBSCRIBE TOPIC TEST
        # =================================================

        test_topic = "traffic/test"
        test_payload = "TEST_FROM_RENDER"

        sub_result = mqtt_client.subscribe(
            test_topic,
            qos=1
        )

        print(
            "TEST SUBSCRIBE RC:",
            sub_result[0]
        )

        print(
            "TEST SUBSCRIBE MID:",
            sub_result[1]
        )

        if sub_result[0] != mqtt.MQTT_ERR_SUCCESS:

            return jsonify({
                "success": False,
                "message": "Khong subscribe duoc topic test",
                "rc": sub_result[0],
                "mid": sub_result[1]
            }), 500

        # =================================================
        # PUBLISH TEST
        #
        # GIỮ QoS 0.
        # Đây KHÔNG phải đường điều khiển thực tế.
        # Ta xác nhận broker bằng cách nhận lại message.
        # =================================================

        result = mqtt_client.publish(
            test_topic,
            test_payload,
            qos=0,
            retain=False
        )

        print(
            "TEST TOPIC:",
            test_topic
        )

        print(
            "TEST PAYLOAD:",
            test_payload
        )

        print(
            "TEST PUBLISH RC:",
            result.rc
        )

        print(
            "TEST PUBLISH MID:",
            result.mid
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            return jsonify({
                "success": False,
                "message": "MQTT publish loi",
                "rc": result.rc,
                "mid": result.mid
            }), 500

        # =================================================
        # CHỜ MESSAGE QUAY LẠI QUA BROKER
        # =================================================

        print(
            "MQTT TEST: DANG CHO MESSAGE QUAY LAI TU BROKER..."
        )

        received = mqtt_test_event.wait(timeout=5)

        with mqtt_test_lock:
            received_payload = mqtt_test_last_payload
            received_topic = mqtt_test_last_topic

        print(
            "MQTT TEST: RECEIVED =",
            received
        )

        print(
            "MQTT TEST: RECEIVED TOPIC =",
            received_topic
        )

        print(
            "MQTT TEST: RECEIVED PAYLOAD =",
            received_payload
        )

        print("================================")

        if received and received_payload == test_payload:

            print(
                "MQTT TEST: THANH CONG - BROKER DA NHAN VA GUI LAI MESSAGE"
            )

            return jsonify({
                "success": True,
                "broker_confirmed": True,
                "message": "Render -> HiveMQ -> Render OK",
                "topic": received_topic,
                "payload": received_payload,
                "publish_rc": result.rc,
                "publish_mid": result.mid
            })

        print(
            "MQTT TEST: KHONG NHAN LAI MESSAGE TU BROKER"
        )

        return jsonify({
            "success": False,
            "broker_confirmed": False,
            "message": (
                "Paho da chap nhan publish "
                "nhung Render khong nhan lai message tu broker"
            ),
            "topic": test_topic,
            "payload": test_payload,
            "publish_rc": result.rc,
            "publish_mid": result.mid,
            "mqtt_connected": mqtt_client.is_connected()
        }), 502

    except Exception as e:

        print()
        print("================================")
        print("MQTT TEST ERROR")
        print(
            "LOI:",
            repr(e)
        )
        print("================================")

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500



# =========================================================
# API TEST MQTT DIRECT CLIENT
#
# DUNG DE KIEM TRA RIENG DUONG:
# Render -> HiveMQ
#
# Client nay HOAN TOAN DOC LAP voi mqtt_client chinh.
# Khong dung cho dieu khien thuc te.
# =========================================================

@app.route(
    "/api/test-mqtt-direct",
    methods=["GET"]
)
def test_mqtt_direct():

    client = None
    connected_event = threading.Event()
    subscribed_event = threading.Event()
    published_event = threading.Event()
    result_data = {
        "connected": False,
        "subscribed": False,
        "published": False,
        "connect_reason": None,
        "subscribe_reason": None,
        "publish_reason": None
    }

    test_topic = "traffic/render_direct_test_" + uuid.uuid4().hex[:8]
    test_payload = "DIRECT_TEST_FROM_RENDER"

    def direct_on_connect(c, userdata, flags, reason_code, properties):
        result_data["connect_reason"] = str(reason_code)

        print("DIRECT MQTT CONNECT REASON:", reason_code)

        if reason_code == 0:
            result_data["connected"] = True
            print("DIRECT MQTT: CONNECT THANH CONG")
        else:
            print("DIRECT MQTT: CONNECT THAT BAI")

        connected_event.set()

    def direct_on_subscribe(c, userdata, mid, reason_codes, properties):
        print("DIRECT MQTT SUBSCRIBE REASON:", reason_codes)

        result_data["subscribe_reason"] = str(reason_codes)

        if not reason_codes:
            ["subscribed"] = False
            print("DIRECT MQTT: SUBSCRIBE THAT BAI")
            subscribed_event.set()
            return

    # Paho MQTT v2 trả về ReasonCode object
        result_data["subscribed"] = all(
            not reason.is_failure for reason in reason_codes
        )   

        if result_data["subscribed"]:
            print("DIRECT MQTT: SUBSCRIBE THANH CONG")
        else:
            print("DIRECT MQTT: SUBSCRIBE THAT BAI")

        subscribed_event.set()

    def direct_on_publish(c, userdata, mid, reason_code, properties):
        print("DIRECT MQTT PUBLISH MID:", mid)
        print("DIRECT MQTT PUBLISH REASON:", reason_code)
        result_data["publish_reason"] = str(reason_code)
        try:
            result_data["published"] = (
                int(reason_code) == 0
            )
        except Exception:
            result_data["published"] = False
        published_event.set()

    def direct_on_disconnect(c, userdata, flags, reason_code, properties):
        print("DIRECT MQTT DISCONNECT REASON:", reason_code)

    def direct_on_log(c, userdata, level, buf):
        print("DIRECT MQTT LOG:", buf)

    try:

        print()
        print("========================================")
        print("DIRECT MQTT TEST BAT DAU")
        print("========================================")
        print("BROKER:", MQTT_BROKER)
        print("PORT:", MQTT_PORT)
        print("USERNAME:", MQTT_USERNAME)
        print("TOPIC:", test_topic)
        print("PAYLOAD:", test_payload)
        print("========================================")

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=(
                "render_direct_"
                + uuid.uuid4().hex[:10]
            ),
            protocol=mqtt.MQTTv311
        )

        client.username_pw_set(
            MQTT_USERNAME,
            MQTT_PASSWORD
        )

        client.tls_set(
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )

        client.on_connect = direct_on_connect
        client.on_subscribe = direct_on_subscribe
        client.on_publish = direct_on_publish
        client.on_disconnect = direct_on_disconnect
        client.on_log = direct_on_log

        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            60
        )

        client.loop_start()

        print("DIRECT MQTT: DANG CHO CONNECT...")

        if not connected_event.wait(timeout=10):
            return jsonify({
                "success": False,
                "stage": "connect",
                "message": "Client rieng khong nhan duoc CONNACK trong 10 giay",
                "connected": client.is_connected(),
                "topic": test_topic
            }), 502

        if not result_data["connected"]:
            return jsonify({
                "success": False,
                "stage": "connect",
                "message": "HiveMQ tu choi ket noi client test",
                "connect_reason": result_data["connect_reason"],
                "topic": test_topic
            }), 502

        sub_result = client.subscribe(
            test_topic,
            qos=1
        )

        print("DIRECT MQTT SUBSCRIBE RC:", sub_result[0])
        print("DIRECT MQTT SUBSCRIBE MID:", sub_result[1])

        if sub_result[0] != mqtt.MQTT_ERR_SUCCESS:
            return jsonify({
                "success": False,
                "stage": "subscribe_call",
                "message": "Paho khong tao duoc SUBSCRIBE",
                "rc": sub_result[0],
                "mid": sub_result[1],
                "topic": test_topic
            }), 502

        print("DIRECT MQTT: DANG CHO SUBACK...")

        if not subscribed_event.wait(timeout=5):
            return jsonify({
                "success": False,
                "stage": "subscribe_ack",
                "message": "Khong nhan duoc SUBACK trong 5 giay",
                "topic": test_topic,
                "subscribe_rc": sub_result[0],
                "subscribe_mid": sub_result[1]
            }), 502

        if not result_data["subscribed"]:
            return jsonify({
                "success": False,
                "stage": "subscribe_ack",
                "message": "HiveMQ khong chap nhan SUBSCRIBE",
                "subscribe_reason": result_data["subscribe_reason"],
                "topic": test_topic
            }), 502

        pub_result = client.publish(
            test_topic,
            test_payload,
            qos=1,
            retain=True
        )

        print("DIRECT MQTT PUBLISH RC:", pub_result.rc)
        print("DIRECT MQTT PUBLISH MID:", pub_result.mid)

        if pub_result.rc != mqtt.MQTT_ERR_SUCCESS:
            return jsonify({
                "success": False,
                "stage": "publish_call",
                "message": "Paho khong tao duoc PUBLISH",
                "publish_rc": pub_result.rc,
                "publish_mid": pub_result.mid,
                "topic": test_topic,
                "payload": test_payload
            }), 502

        print("DIRECT MQTT: DANG CHO PUBACK...")

        if not published_event.wait(timeout=10):
            return jsonify({
                "success": False,
                "stage": "publish_ack",
                "message": "Khong nhan duoc PUBACK trong 10 giay",
                "publish_rc": pub_result.rc,
                "publish_mid": pub_result.mid,
                "connected": client.is_connected(),
                "topic": test_topic,
                "payload": test_payload
            }), 502

        if not result_data["published"]:
            return jsonify({
                "success": False,
                "stage": "publish_ack",
                "message": "HiveMQ khong xac nhan PUBLISH",
                "publish_reason": result_data["publish_reason"],
                "publish_rc": pub_result.rc,
                "publish_mid": pub_result.mid,
                "topic": test_topic,
                "payload": test_payload
            }), 502

        print("DIRECT MQTT TEST: THANH CONG")
        print("DIRECT MQTT TEST: HiveMQ da xac nhan PUBACK")
        print("========================================")

        return jsonify({
            "success": True,
            "broker_confirmed": True,
            "message": "Render -> HiveMQ OK voi MQTT client doc lap",
            "stage": "publish_ack",
            "connected": True,
            "subscribed": True,
            "published": True,
            "connect_reason": result_data["connect_reason"],
            "subscribe_reason": result_data["subscribe_reason"],
            "publish_reason": result_data["publish_reason"],
            "publish_rc": pub_result.rc,
            "publish_mid": pub_result.mid,
            "topic": test_topic,
            "payload": test_payload,
            "retain": True,
            "qos": 1
        })

    except Exception as e:

        print()
        print("========================================")
        print("DIRECT MQTT TEST ERROR")
        print("LOI:", repr(e))
        print("========================================")

        return jsonify({
            "success": False,
            "stage": "exception",
            "message": str(e),
            "topic": test_topic,
            "payload": test_payload
        }), 500

    finally:

        if client is not None:
            try:
                client.loop_stop()
            except Exception:
                pass

            try:
                if client.is_connected():
                    client.disconnect()
            except Exception:
                pass



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

                "message":
                    "Khong co du lieu JSON"

            }), 400

        command = data.get(
            "command"
        )

        if not command:

            return jsonify({

                "success": False,

                "message":
                    "Thieu command"

            }), 400

        print()
        print("==============================")
        print(
            "CHUAN BI GUI LENH:",
            command
        )
        print("==============================")

        # =================================================
        # KIỂM TRA MQTT
        # =================================================

        print(
            "MQTT CONNECTED:",
            mqtt_client.is_connected()
        )

        if not mqtt_client.is_connected():

            print(
                "MQTT: CHUA KET NOI"
            )

            return jsonify({

                "success": False,

                "message":
                    "MQTT chua ket noi"

            }), 503

        # =================================================
        # GỬI LỆNH SANG ESP32
        #
        # GIỮ QoS 0 ĐỂ API PHẢN HỒI NHANH
        # KHÔNG dùng wait_for_publish()
        # =================================================

        result = mqtt_client.publish(

            TOPIC_CONTROL,

            command,

            qos=0,

            retain=False

        )

        print(
            "CONTROL PUBLISH RC:",
            result.rc
        )

        print(
            "CONTROL PUBLISH MID:",
            result.mid
        )

        # =================================================
        # KIỂM TRA KẾT QUẢ PUBLISH
        # =================================================

        if result.rc != mqtt.MQTT_ERR_SUCCESS:

            print(
                "MQTT PUBLISH LOI"
            )

            return jsonify({

                "success": False,

                "message":
                    "MQTT publish loi",

                "rc":
                    result.rc

            }), 500

        print(
            "MQTT CONTROL: DA GUI LENH:",
            command
        )

        return jsonify({

            "success": True,

            "command":
                command

        })

    except Exception as e:

        print(
            "API CONTROL ERROR:",
            repr(e)
        )

        return jsonify({

            "success": False,

            "message":
                str(e)

        }), 500


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