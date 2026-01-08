import sys, time, threading, queue, re
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QTextEdit, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QFont

import serial
import serial.tools.list_ports


# ================= SIGNAL BRIDGE =================
class SerialSignals(QObject):
    rx = Signal(str)
    log = Signal(str)
    auto = Signal(str)


# ================= MAIN WINDOW =================
class RS485Monitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RS485 Power Monitor")
        self.setFixedSize(900, 400)

        self.ser = None
        self.running = False
        self.auto_connecting = False
        self.queue = queue.Queue()
        self.signals = SerialSignals()

        self._colors()
        self._ui()
        self._connect_signals()
        self.scan_ports()

    # ================= COLORS =================
    def _colors(self):
        self.BG = "#0b1220"
        self.PANEL = "#111827"
        self.CARD = "#0f172a"
        self.TEXT = "#e5e7eb"
        self.MUTED = "#9ca3af"
        self.BLUE = "#38bdf8"
        self.GREEN = "#22c55e"
        self.RED = "#ef4444"
        self.GRAY = "#334155"
        self.NEW = "#ffffff"

    # ================= UI =================
    def _ui(self):
        root = QWidget()
        root.setStyleSheet(f"background:{self.BG};")
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # HEADER
        header = QHBoxLayout()
        title = QLabel("RS485 Power Monitor")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color:{self.TEXT}")
        header.addWidget(title)

        header.addStretch()

        self.status = QLabel("● Disconnected")
        self.status.setFont(QFont("Segoe UI", 12))
        self.status.setStyleSheet(f"color:{self.RED}")
        header.addWidget(self.status)

        main_layout.addLayout(header)

        # BODY
        body = QHBoxLayout()
        main_layout.addLayout(body, 1)

        # SIDEBAR
        side = QFrame()
        side.setFixedWidth(260)
        side.setStyleSheet(f"background:{self.PANEL}; border-radius:8px;")
        body.addWidget(side)

        side_l = QVBoxLayout(side)
        side_l.setContentsMargins(12, 12, 12, 12)

        def section(txt):
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{self.MUTED}")
            side_l.addWidget(lbl)

        section("SERIAL")
        self.port_cb = QComboBox()
        self.baud_cb = QComboBox()
        self.baud_cb.addItems(["9600","19200","38400","57600","115200"])
        self.baud_cb.setCurrentText("115200")

        #for w in (self.port_cb, self.baud_cb):
          #  w.setStyleSheet("padding:6px, background:#1e293b;color:#e5e7eb;")
        combo_style = """
                        QComboBox {
                            background: #ffffff;
                            color: #000000;
                            border: 1px solid #cbd5e1;
                            border-radius: 6px;
                            padding: 6px;
                        }

                        QComboBox:hover {
                            border-color: #60a5fa;
                        }

                        QComboBox:focus {
                            border-color: #3b82f6;
                        }

                        QComboBox::drop-down {
                            border: none;
                            width: 24px;
                        }

                        /* Dropdown list */
                        QComboBox QAbstractItemView {
                            color: #000000;
                            border: 1px solid #cbd5e1;
                            border-radius: 10px;
                            outline: none;
                        }

                        /* Each item */
                        QComboBox QAbstractItemView::item {
                            background: #ffffff;
                            color: #000000;
                            padding: 1px 2px;
                            border: 2px solid #e5e7eb;
                            border-radius: 6px;
                        }

                        /* Hover */
                        QComboBox QAbstractItemView::item:selected {
                            background: #e0f2fe;
                            color: #000000;
                        }
                    """
                        

        self.port_cb.setStyleSheet(combo_style)
        self.baud_cb.setStyleSheet(combo_style)


        side_l.addWidget(self.port_cb)
        side_l.addWidget(self.baud_cb)

        self.btn_scan = QPushButton("Scan Ports")
        self.btn_conn = QPushButton("Connect / Disconnect")
        self.btn_auto = QPushButton("Auto Connect")

        for b in (self.btn_scan, self.btn_conn, self.btn_auto):
            b.setFixedHeight(36)
            b.setStyleSheet("background:#334155;")

        side_l.addWidget(self.btn_scan)
        side_l.addWidget(self.btn_conn)
        side_l.addWidget(self.btn_auto)

        section("COMMAND")

        self.btn_rs = QPushButton("Send rs")
        self.btn_r = QPushButton("Send r")
        self.btn_rs.setFixedHeight(36)
        self.btn_r.setFixedHeight(36)

        self.btn_rs.setStyleSheet("background:#22c55e;")
        self.btn_r.setStyleSheet("background:#fb923c;")

        side_l.addWidget(self.btn_rs)
        side_l.addWidget(self.btn_r)
        side_l.addStretch()

        # MAIN CONTENT
        main = QVBoxLayout()
        body.addLayout(main, 1)

        cards = QGridLayout()
        main.addLayout(cards)

        self.v_lbl = self._card("Voltage", "V")
        self.i_lbl = self._card("Current", "mA")
        self.p_lbl = self._card("Power", "W")

        cards.addWidget(self.v_lbl[0], 0, 0)
        cards.addWidget(self.i_lbl[0], 0, 1)
        cards.addWidget(self.p_lbl[0], 0, 2)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(
            f"background:#020617;color:{self.TEXT};font-family:Consolas;"
        )
        main.addWidget(self.log, 1)

    def _card(self, title, unit):
        frame = QFrame()
        frame.setStyleSheet(f"background:{self.CARD};border-radius:10px;")
        frame.setMinimumHeight(220)

        l = QVBoxLayout(frame)
        l.setAlignment(Qt.AlignCenter)

        t = QLabel(title)
        t.setStyleSheet(f"color:{self.MUTED}")
        l.addWidget(t)

        val = QLabel("--")
        val.setFont(QFont("Segoe UI", 46, QFont.Bold))
        val.setStyleSheet(f"color:{self.BLUE}")
        l.addWidget(val)

        u = QLabel(unit)
        u.setStyleSheet(f"color:{self.MUTED}")
        l.addWidget(u)

        return frame, val

    # ================= SERIAL =================
    def scan_ports(self):
        self.port_cb.clear()
        self.port_cb.addItems([p.device for p in serial.tools.list_ports.comports()])
        self._log("Ports scanned")

    def toggle_connection(self):
        if self.ser:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port_cb.currentText(),
                                     int(self.baud_cb.currentText()), timeout=0.2)
            self.running = True
            threading.Thread(target=self._reader, daemon=True).start()
            self.status.setText("● Connected")
            self.status.setStyleSheet(f"color:{self.GREEN}")
            self._log("Connected")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
        self.ser = None
        self.status.setText("● Disconnected")
        self.status.setStyleSheet(f"color:{self.RED}")
        self._log("Disconnected")

    def send_cmd(self, cmd):
        if self.ser:
            self.ser.write((cmd + "\n").encode())
            self._log(f"TX: {cmd}")

    def _reader(self):
        buf = ""
        while self.running:
            if self.ser and self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    self.signals.rx.emit(line.strip())
            time.sleep(0.01)

    # ================= PARSER =================
    def _parse(self, line):
        try:
            if "," in line:
                v, i, p = map(float, line.split(",")[:3])
                self.v_lbl[1].setText(f"{v:.2f}")
                self.i_lbl[1].setText(f"{i:.3f}")
                self.p_lbl[1].setText(f"{p:.2f}")
                return

            m = re.search(r"([VIA]|P)\s*=?\s*([-+]?\d*\.?\d+)", line)
            if not m:
                return

            k, v = m.group(1), float(m.group(2))
            if k == "V":
                self.v_lbl[1].setText(f"{v:.2f}")
            elif k in ("I", "A"):
                self.i_lbl[1].setText(f"{v:.3f}")
            elif k == "P":
                self.p_lbl[1].setText(f"{v:.2f}")
        except:
            pass

    # ================= LOG =================
    def _log(self, msg):
        t = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{t}] {msg}")

    # ================= SIGNALS =================
    def _connect_signals(self):
        self.btn_scan.clicked.connect(self.scan_ports)
        self.btn_conn.clicked.connect(self.toggle_connection)
        self.btn_rs.clicked.connect(lambda: self.send_cmd("rs"))
        self.btn_r.clicked.connect(lambda: self.send_cmd("r"))

        self.signals.rx.connect(self._on_rx)

    def _on_rx(self, line):
        self._log("RX: " + line)
        self._parse(line)


# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RS485Monitor()
    win.show()
    sys.exit(app.exec())
