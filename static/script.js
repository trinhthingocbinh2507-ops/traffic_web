// ============================================================
// CẤU HÌNH API
// ============================================================

const API_STATUS = "/api/status";
const API_HISTORY = "/api/history";
const API_CONTROL = "/api/control";

// ============================================================
// BIẾN BIỂU ĐỒ
// ============================================================

let vehicleChart = null;
let historyChart = null;

// ============================================================
// HÀM GÁN TEXT
// ============================================================

function setText(id, value) {
  const element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

// ============================================================
// CẬP NHẬT SỐ XE 4 HƯỚNG
// ============================================================

function capNhatSoXe(h1, h2, h3, h4) {
  setText("received1", h1);
  setText("received2", h2);
  setText("received3", h3);
  setText("received4", h4);
}

// ============================================================
// CẬP NHẬT TRẠNG THÁI ĐÈN
// ============================================================

function capNhatTrangThaiDen(phase, timeLeft, xanh1, vang1, xanh2, vang2) {
  let group1Light = "ĐỎ";
  let group2Light = "ĐỎ";

  let group1Time = 0;
  let group2Time = 0;

  // --------------------------------------------------------
  // NHÓM 1 XANH
  // Hướng 1 + Hướng 3 xanh
  // Hướng 2 + Hướng 4 đỏ
  // --------------------------------------------------------

  if (phase === "NHOM1_XANH" || phase === "NHOM 1 XANH") {
    group1Light = "XANH";
    group2Light = "ĐỎ";

    group1Time = timeLeft;

    // Nhóm 2 phải chờ:
    // thời gian xanh nhóm 1 + thời gian vàng nhóm 1
    group2Time = timeLeft + vang1;
  }

  // --------------------------------------------------------
  // NHÓM 1 VÀNG
  // --------------------------------------------------------
  else if (phase === "NHOM1_VANG" || phase === "NHOM 1 VANG") {
    group1Light = "VÀNG";
    group2Light = "ĐỎ";

    group1Time = timeLeft;

    group2Time = timeLeft;
  }

  // --------------------------------------------------------
  // NHÓM 2 XANH
  // --------------------------------------------------------
  else if (phase === "NHOM2_XANH" || phase === "NHOM 2 XANH") {
    group1Light = "ĐỎ";
    group2Light = "XANH";

    group1Time = timeLeft + vang2;

    group2Time = timeLeft;
  }

  // --------------------------------------------------------
  // NHÓM 2 VÀNG
  // --------------------------------------------------------
  else if (phase === "NHOM2_VANG" || phase === "NHOM 2 VANG") {
    group1Light = "ĐỎ";
    group2Light = "VÀNG";

    group1Time = timeLeft;
    group2Time = timeLeft;
  }

  // --------------------------------------------------------
  // ALL RED
  // --------------------------------------------------------
  else if (phase === "ALL_RED" || phase === "ALL RED") {
    group1Light = "ĐỎ";
    group2Light = "ĐỎ";

    group1Time = timeLeft;
    group2Time = timeLeft;
  }

  // --------------------------------------------------------
  // HIỂN THỊ
  // --------------------------------------------------------

  setText("group1Light", group1Light);
  setText("group2Light", group2Light);

  setText("group1Time", group1Time);
  setText("group2Time", group2Time);

  // --------------------------------------------------------
  // ĐỔI MÀU TRẠNG THÁI
  // --------------------------------------------------------

  const group1Element = document.getElementById("group1Light");

  const group2Element = document.getElementById("group2Light");

  if (group1Element) {
    group1Element.classList.remove("light-green", "light-yellow", "light-red");

    if (group1Light === "XANH") {
      group1Element.classList.add("light-green");
    } else if (group1Light === "VÀNG") {
      group1Element.classList.add("light-yellow");
    } else {
      group1Element.classList.add("light-red");
    }
  }

  if (group2Element) {
    group2Element.classList.remove("light-green", "light-yellow", "light-red");

    if (group2Light === "XANH") {
      group2Element.classList.add("light-green");
    } else if (group2Light === "VÀNG") {
      group2Element.classList.add("light-yellow");
    } else {
      group2Element.classList.add("light-red");
    }
  }
}

// ============================================================
// CẬP NHẬT THỜI GIAN ĐÈN
// ============================================================

function capNhatThoiGian(xanh1, vang1, xanh2, vang2) {
  const red1 = Number(xanh2) + Number(vang2);
  const red2 = Number(xanh1) + Number(vang1);

  setText("green1", xanh1);
  setText("yellow1", vang1);
  setText("red1", red1);

  setText("green2", xanh2);
  setText("yellow2", vang2);
  setText("red2", red2);
}

// ============================================================
// TÍNH THỜI GIAN ĐỎ MANUAL
// ============================================================

function capNhatThoiGianManual() {
  const green1Element = document.getElementById("manualGreen1");

  const yellow1Element = document.getElementById("manualYellow1");

  const red1Element = document.getElementById("manualRed1");

  const green2Element = document.getElementById("manualGreen2");

  const yellow2Element = document.getElementById("manualYellow2");

  const red2Element = document.getElementById("manualRed2");

  if (
    !green1Element ||
    !yellow1Element ||
    !red1Element ||
    !green2Element ||
    !yellow2Element ||
    !red2Element
  ) {
    return;
  }

  const green1 = Number(green1Element.value) || 0;

  const yellow1 = Number(yellow1Element.value) || 0;

  const green2 = Number(green2Element.value) || 0;

  const yellow2 = Number(yellow2Element.value) || 0;

  // Đỏ nhóm 1
  // = Xanh nhóm 2 + Vàng nhóm 2

  const red1 = green2 + yellow2;

  // Đỏ nhóm 2
  // = Xanh nhóm 1 + Vàng nhóm 1

  const red2 = green1 + yellow1;

  red1Element.value = red1;
  red2Element.value = red2;

  setText("calculationRed1", `${green2} + ${yellow2} = ${red1} giây`);

  setText("calculationRed2", `${green1} + ${yellow1} = ${red2} giây`);
}

// ============================================================
// ĐỔI GIAO DIỆN AUTO / MANUAL
// ============================================================

function capNhatGiaoDienCheDo(mode) {
  const manualPanel = document.getElementById("manualPanel");

  const autoButton = document.getElementById("autoButton");

  const manualButton = document.getElementById("manualButton");

  const controlStatus = document.getElementById("controlStatus");

  const manualInputs = [
    document.getElementById("manualGreen1"),
    document.getElementById("manualYellow1"),
    document.getElementById("manualGreen2"),
    document.getElementById("manualYellow2"),
    document.getElementById("sendManualTime"),
  ];

  // ========================================================
  // AUTO
  // ========================================================

  if (mode === "AUTO") {
    if (manualPanel) {
      manualPanel.classList.remove("manual-enabled");

      manualPanel.classList.add("manual-disabled");
    }

    manualInputs.forEach(function (element) {
      if (element) {
        element.disabled = true;
      }
    });

    if (autoButton) {
      autoButton.classList.add("active-mode");
    }

    if (manualButton) {
      manualButton.classList.remove("active-mode");
    }

    if (controlStatus) {
      controlStatus.innerHTML = "Chế độ hiện tại: <strong>AUTO</strong>";
    }
  }

  // ========================================================
  // MANUAL
  // ========================================================
  else if (mode === "MANUAL") {
    if (manualPanel) {
      manualPanel.classList.remove("manual-disabled");

      manualPanel.classList.add("manual-enabled");
    }

    manualInputs.forEach(function (element) {
      if (element) {
        element.disabled = false;
      }
    });

    // Ô đỏ vẫn chỉ để hiển thị
    const red1 = document.getElementById("manualRed1");

    const red2 = document.getElementById("manualRed2");

    if (red1) {
      red1.disabled = true;
      red1.readOnly = true;
    }

    if (red2) {
      red2.disabled = true;
      red2.readOnly = true;
    }

    if (manualButton) {
      manualButton.classList.add("active-mode");
    }

    if (autoButton) {
      autoButton.classList.remove("active-mode");
    }

    if (controlStatus) {
      controlStatus.innerHTML = "Chế độ hiện tại: <strong>MANUAL</strong>";
    }

    capNhatThoiGianManual();
  }
}

// ============================================================
// GỬI MQTT QUA FLASK
// ============================================================

async function guiMQTT(topic, data) {
  try {
    const response = await fetch(API_CONTROL, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        topic: topic,
        command: data,
      }),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      throw new Error(result.message || "Không gửi được lệnh");
    }

    console.log("Đã gửi:", data);

    return true;
  } catch (error) {
    console.error("Lỗi gửi MQTT:", error);

    setText("manualTimeStatus", "❌ Không gửi được lệnh: " + error.message);

    return false;
  }
}

// ============================================================
// CHỌN AUTO
// ============================================================

async function chonAuto() {
  const thanhCong = await guiMQTT("traffic/control", "AUTO");

  if (thanhCong) {
    capNhatGiaoDienCheDo("AUTO");

    setText("manualTimeStatus", "Đã chuyển sang chế độ AUTO.");
  }
}

// ============================================================
// CHỌN MANUAL
// ============================================================

async function chonManual() {
  const thanhCong = await guiMQTT("traffic/control", "MANUAL");

  if (thanhCong) {
    capNhatGiaoDienCheDo("MANUAL");

    setText("manualTimeStatus", "Đã chuyển sang chế độ MANUAL.");
  }
}

// ============================================================
// GỬI THỜI GIAN MANUAL
// ============================================================

async function guiThoiGianManual() {
  const green1 = Number(document.getElementById("manualGreen1").value);

  const yellow1 = Number(document.getElementById("manualYellow1").value);

  const green2 = Number(document.getElementById("manualGreen2").value);

  const yellow2 = Number(document.getElementById("manualYellow2").value);

  // --------------------------------------------------------
  // KIỂM TRA
  // --------------------------------------------------------

  if (green1 <= 0 || yellow1 <= 0 || green2 <= 0 || yellow2 <= 0) {
    setText("manualTimeStatus", "❌ Thời gian phải lớn hơn 0.");

    return;
  }

  // --------------------------------------------------------
  // TÍNH ĐỎ
  // --------------------------------------------------------

  const red1 = green2 + yellow2;

  const red2 = green1 + yellow1;

  // --------------------------------------------------------
  // GỬI ESP32
  // --------------------------------------------------------

  const data = `MANUAL_TIME,${green1},${yellow1},${green2},${yellow2}`;

  const thanhCong = await guiMQTT("traffic/control", data);

  if (!thanhCong) {
    return;
  }

  // --------------------------------------------------------
  // HIỂN THỊ
  // --------------------------------------------------------

  setText(
    "manualTimeStatus",
    `✅ Đã gửi: Xanh1=${green1}s, Vàng1=${yellow1}s, ` +
      `Đỏ1=${red1}s | ` +
      `Xanh2=${green2}s, Vàng2=${yellow2}s, ` +
      `Đỏ2=${red2}s`,
  );

  capNhatThoiGian(green1, yellow1, green2, yellow2);

  setText("controlStatus", "Đã gửi thời gian MANUAL thành công.");
}

// ============================================================
// KHỞI TẠO BIỂU ĐỒ HIỆN TẠI
// ============================================================

function taoBieuDoHienTai() {
  const canvas = document.getElementById("vehicleChart");

  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");

  vehicleChart = new Chart(ctx, {
    type: "bar",

    data: {
      labels: ["Hướng 1", "Hướng 2", "Hướng 3", "Hướng 4"],

      datasets: [
        {
          label: "Số xe hiện tại",

          data: [0, 0, 0, 0],
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      scales: {
        y: {
          beginAtZero: true,

          ticks: {
            stepSize: 1,
          },
        },
      },

      plugins: {
        legend: {
          display: true,
        },
      },
    },
  });
}

// ============================================================
// CẬP NHẬT BIỂU ĐỒ HIỆN TẠI
// ============================================================

function capNhatBieuDoHienTai(h1, h2, h3, h4) {
  if (!vehicleChart) {
    return;
  }

  vehicleChart.data.datasets[0].data = [h1, h2, h3, h4];

  vehicleChart.update();
}

// ============================================================
// TẠO BIỂU ĐỒ LỊCH SỬ
// ============================================================

function taoBieuDoLichSu(history) {
  const canvas = document.getElementById("historyChart");

  if (!canvas) {
    return;
  }

  const ctx = canvas.getContext("2d");

  const labels = history.map((item) => item.time);

  const h1 = history.map((item) => item.h1);

  const h2 = history.map((item) => item.h2);

  const h3 = history.map((item) => item.h3);

  const h4 = history.map((item) => item.h4);

  if (historyChart) {
    historyChart.data.labels = labels;

    historyChart.data.datasets[0].data = h1;

    historyChart.data.datasets[1].data = h2;

    historyChart.data.datasets[2].data = h3;

    historyChart.data.datasets[3].data = h4;

    historyChart.update();

    return;
  }

  historyChart = new Chart(ctx, {
    type: "line",

    data: {
      labels: labels,

      datasets: [
        {
          label: "Hướng 1",
          data: h1,
          tension: 0.3,
        },

        {
          label: "Hướng 2",
          data: h2,
          tension: 0.3,
        },

        {
          label: "Hướng 3",
          data: h3,
          tension: 0.3,
        },

        {
          label: "Hướng 4",
          data: h4,
          tension: 0.3,
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      interaction: {
        mode: "index",

        intersect: false,
      },

      scales: {
        y: {
          beginAtZero: true,

          ticks: {
            stepSize: 1,
          },
        },
      },
    },
  });
}

// ============================================================
// LẤY LỊCH SỬ TỪ FLASK
// ============================================================

async function capNhatBieuDoLichSu() {
  try {
    const response = await fetch(API_HISTORY);

    if (!response.ok) {
      throw new Error("Không lấy được lịch sử.");
    }

    const history = await response.json();

    if (!Array.isArray(history)) {
      throw new Error("Dữ liệu lịch sử không hợp lệ.");
    }

    taoBieuDoLichSu(history);
  } catch (error) {
    console.error("Lỗi biểu đồ lịch sử:", error);
  }
}

// ============================================================
// LẤY TRẠNG THÁI TỪ FLASK
// ============================================================

async function capNhatTrangThai() {
  try {
    const response = await fetch(API_STATUS);

    if (!response.ok) {
      throw new Error("Không lấy được trạng thái.");
    }

    const data = await response.json();

    const h1 = Number(data.h1) || 0;

    const h2 = Number(data.h2) || 0;

    const h3 = Number(data.h3) || 0;

    const h4 = Number(data.h4) || 0;

    const phase = data.phase || "ALL_RED";

    const timeLeft = Number(data.time) || 0;

    const xanh1 = Number(data.xanh1) || 15;

    const vang1 = Number(data.vang1) || 3;

    const xanh2 = Number(data.xanh2) || 15;

    const vang2 = Number(data.vang2) || 3;

    // ----------------------------------------------------
    // SỐ XE
    // ----------------------------------------------------

    capNhatSoXe(h1, h2, h3, h4);

    // ----------------------------------------------------
    // TRẠNG THÁI ĐÈN
    // ----------------------------------------------------

    capNhatTrangThaiDen(phase, timeLeft, xanh1, vang1, xanh2, vang2);

    // ----------------------------------------------------
    // THỜI GIAN
    // ----------------------------------------------------

    capNhatThoiGian(xanh1, vang1, xanh2, vang2);

    // ----------------------------------------------------
    // BIỂU ĐỒ
    // ----------------------------------------------------

    capNhatBieuDoHienTai(h1, h2, h3, h4);
  } catch (error) {
    console.error("Lỗi cập nhật trạng thái:", error);
  }
}

// ============================================================
// SỰ KIỆN VIDEO
// ============================================================

function khoiTaoVideo() {
  const video = document.getElementById("trafficVideo");

  if (!video) {
    return;
  }

  video.addEventListener("play", function () {
    setText("videoStatus", "Trạng thái video: Đang phát.");
  });

  video.addEventListener("pause", function () {
    setText("videoStatus", "Trạng thái video: Đang tạm dừng.");
  });

  video.addEventListener("ended", function () {
    setText("videoStatus", "Trạng thái video: Đã kết thúc.");
  });

  video.addEventListener("error", function () {
    setText("videoStatus", "Trạng thái video: Lỗi video.");
  });
}

// ============================================================
// KHỞI TẠO TRANG
// ============================================================

document.addEventListener("DOMContentLoaded", function () {
  // ----------------------------------------------------
  // Mặc định AUTO
  // ----------------------------------------------------

  capNhatGiaoDienCheDo("AUTO");

  // ----------------------------------------------------
  // Nút AUTO
  // ----------------------------------------------------

  const autoButton = document.getElementById("autoButton");

  if (autoButton) {
    autoButton.addEventListener("click", chonAuto);
  }

  // ----------------------------------------------------
  // Nút MANUAL
  // ----------------------------------------------------

  const manualButton = document.getElementById("manualButton");

  if (manualButton) {
    manualButton.addEventListener("click", chonManual);
  }

  // ----------------------------------------------------
  // Ô nhập MANUAL
  // ----------------------------------------------------

  const manualInputs = [
    document.getElementById("manualGreen1"),

    document.getElementById("manualYellow1"),

    document.getElementById("manualGreen2"),

    document.getElementById("manualYellow2"),
  ];

  manualInputs.forEach(function (element) {
    if (element) {
      element.addEventListener("input", capNhatThoiGianManual);
    }
  });

  // ----------------------------------------------------
  // Nút gửi MANUAL TIME
  // ----------------------------------------------------

  const sendButton = document.getElementById("sendManualTime");

  if (sendButton) {
    sendButton.addEventListener("click", guiThoiGianManual);
  }

  // ----------------------------------------------------
  // Video
  // ----------------------------------------------------

  khoiTaoVideo();

  // ----------------------------------------------------
  // Biểu đồ hiện tại
  // ----------------------------------------------------

  taoBieuDoHienTai();

  // ----------------------------------------------------
  // Lấy trạng thái ngay khi mở trang
  // ----------------------------------------------------

  capNhatTrangThai();

  // ----------------------------------------------------
  // Lấy lịch sử ngay khi mở trang
  // ----------------------------------------------------

  capNhatBieuDoLichSu();

  // ----------------------------------------------------
  // Cập nhật trạng thái mỗi 1 giây
  // ----------------------------------------------------

  setInterval(capNhatTrangThai, 1000);

  // ----------------------------------------------------
  // Cập nhật lịch sử mỗi 2 giây
  // ----------------------------------------------------

  setInterval(capNhatBieuDoLichSu, 2000);
});
