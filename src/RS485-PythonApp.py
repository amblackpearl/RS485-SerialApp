import sys, time, threading, queue, re
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QComboBox, QTextEdit, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QMessageBox, QSpacerItem, QSizePolicy
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
        self.auto_timer = QTimer()
        
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
        main_layout.setSpacing(12)

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
        body.setSpacing(16)
        main_layout.addLayout(body, 1)

        # SIDEBAR
        side = QFrame()
        side.setFixedWidth(260)
        side.setStyleSheet(f"background:{self.PANEL}; border-radius:8px;")
        body.addWidget(side)

        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)

        # SERIAL SECTION
        serial_section = QVBoxLayout()
        serial_section.setSpacing(6)
        
        serial_label = QLabel("SERIAL")
        serial_label.setStyleSheet(f"color:{self.MUTED}")
        serial_section.addWidget(serial_label)

        self.port_cb = QComboBox()
        self.baud_cb = QComboBox()
        self.baud_cb.addItems(["9600","19200","38400","57600","115200"])
        self.baud_cb.setCurrentText("115200")

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
            QComboBox QAbstractItemView {
                color: #000000;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                background: #ffffff;
                color: #000000;
                padding: 1px 2px;
                border: 2px solid #e5e7eb;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #e0f2fe;
                color: #000000;
            }
        """

        self.port_cb.setStyleSheet(combo_style)
        self.baud_cb.setStyleSheet(combo_style)

        serial_section.addWidget(self.port_cb)
        serial_section.addWidget(self.baud_cb)

        # BUTTONS SECTION
        buttons_section = QVBoxLayout()
        buttons_section.setSpacing(8)
        
        self.btn_scan = QPushButton("🔍 Scan Ports")
        self.btn_conn = QPushButton("🔌 Connect")
        self.btn_auto = QPushButton("⚡ Auto Connect")
        
        # Button styling
        button_style = """
            QPushButton {
                background-color: #334155;
                color: #e5e7eb;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #475569;
            }
            QPushButton:pressed {
                background-color: #1e293b;
            }
        """
        
        auto_style = """
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:pressed {
                background-color: #15803d;
            }
        """
        
        self.btn_scan.setStyleSheet(button_style)
        self.btn_conn.setStyleSheet(button_style)
        self.btn_auto.setStyleSheet(auto_style)
        
        for b in (self.btn_scan, self.btn_conn, self.btn_auto):
            b.setFixedHeight(40)
            buttons_section.addWidget(b)

        # COMMAND SECTION
        command_section = QVBoxLayout()
        command_section.setSpacing(6)
        
        command_label = QLabel("COMMAND")
        command_label.setStyleSheet(f"color:{self.MUTED}")
        command_section.addWidget(command_label)
        
        # Command buttons in a grid for better alignment
        command_grid = QGridLayout()
        command_grid.setSpacing(8)
        
        self.btn_rs = QPushButton("📤 Send 'rs'")
        self.btn_r = QPushButton("📤 Send 'r'")
        
        self.btn_rs.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        
        self.btn_r.setStyleSheet("""
            QPushButton {
                background-color: #fb923c;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ea580c;
            }
        """)
        
        for b in (self.btn_rs, self.btn_r):
            b.setFixedHeight(40)
        
        command_grid.addWidget(self.btn_rs, 0, 0)
        command_grid.addWidget(self.btn_r, 0, 1)
        
        command_section.addLayout(command_grid)

        # Add all sections to side layout
        side_layout.addLayout(serial_section)
        side_layout.addLayout(buttons_section)
        side_layout.addStretch()
        side_layout.addLayout(command_section)

        # MAIN CONTENT
        main = QVBoxLayout()
        main.setSpacing(12)
        body.addLayout(main, 1)

        cards = QGridLayout()
        cards.setSpacing(12)
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
            f"background:#020617;color:{self.TEXT};font-family:Consolas;border-radius:8px;padding:8px;"
        )
        main.addWidget(self.log, 1)

    def _card(self, title, unit):
        frame = QFrame()
        frame.setStyleSheet(f"""
            background:{self.CARD};
            border-radius:12px;
        """)
        frame.setMinimumHeight(220)

        # Create main layout for the frame
        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a container widget for centering
        container = QWidget()
        container.setObjectName("cardContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Center alignment for the container layout
        container_layout.setAlignment(Qt.AlignCenter)
        container_layout.setSpacing(8)  # Space between title, value, and unit
        
        # Title label
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 12))
        t.setStyleSheet(f"color:{self.MUTED}; padding: 4px;")
        t.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(t)

        # Value label - this is the main number
        val = QLabel("--")
        val.setFont(QFont("Segoe UI", 48, QFont.Bold))
        val.setStyleSheet(f"color:{self.BLUE}; padding: 8px;")
        val.setAlignment(Qt.AlignCenter)
        val.setMinimumWidth(120)  # Ensure consistent width
        container_layout.addWidget(val)

        # Unit label
        u = QLabel(unit)
        u.setFont(QFont("Segoe UI", 12))
        u.setStyleSheet(f"color:{self.MUTED}; padding: 4px;")
        u.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(u)
        
        # Add the centered container to the main layout
        main_layout.addWidget(container)
        
        return frame, val

    # ================= AUTO CONNECT =================
    def toggle_auto_connect(self):
        if not self.auto_connecting:
            self.start_auto_connect()
        else:
            self.stop_auto_connect()

    def start_auto_connect(self):
        self.auto_connecting = True
        self.btn_auto.setText("⏹️ Stop Auto Connect")
        self.btn_auto.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self._log("Auto-connect started")
        
        # Set up timer for auto-connect attempts
        self.auto_timer.timeout.connect(self.auto_connect_attempt)
        self.auto_timer.start(2000)  # Try every 2 seconds
        
        # Try immediately
        self.auto_connect_attempt()

    def stop_auto_connect(self):
        self.auto_connecting = False
        self.btn_auto.setText("⚡ Auto Connect")
        self.btn_auto.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.auto_timer.stop()
        self._log("Auto-connect stopped")

    def auto_connect_attempt(self):
        if self.ser and self.ser.is_open:
            return  # Already connected
            
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            self._log("Auto-connect: No ports available")
            return
            
        # Try each port
        for port in ports:
            try:
                self._log(f"Auto-connect: Trying {port}")
                ser = serial.Serial(
                    port,
                    int(self.baud_cb.currentText()),
                    timeout=0.2
                )
                ser.close()
                
                # If we get here, port is available
                self.port_cb.setCurrentText(port)
                self.connect()
                self._log(f"Auto-connect: Connected to {port}")
                self.stop_auto_connect()  # Stop trying once connected
                return
            except Exception as e:
                continue

    # ================= SERIAL =================
    def scan_ports(self):
        self.port_cb.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb.addItems(ports)
        self._log(f"Scanned {len(ports)} ports")

    def toggle_connection(self):
        if self.ser and self.ser.is_open:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        try:
            self.ser = serial.Serial(
                self.port_cb.currentText(),
                int(self.baud_cb.currentText()),
                timeout=0.2
            )
            self.running = True
            threading.Thread(target=self._reader, daemon=True).start()
            self.status.setText("● Connected")
            self.status.setStyleSheet(f"color:{self.GREEN}")
            self.btn_conn.setText("🔌 Disconnect")
            self._log(f"Connected to {self.port_cb.currentText()}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self._log(f"Connection failed: {str(e)}")

    def disconnect(self):
        self.running = False
        if self.ser:
            self.ser.close()
        self.ser = None
        self.status.setText("● Disconnected")
        self.status.setStyleSheet(f"color:{self.RED}")
        self.btn_conn.setText("🔌 Connect")
        
        # Reset display values
        self.v_lbl[1].setText("--")
        self.i_lbl[1].setText("--")
        self.p_lbl[1].setText("--")
        
        self._log("Disconnected")

    def send_cmd(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + "\n").encode())
                self._log(f"TX: {cmd}")
            except Exception as e:
                self._log(f"Send failed: {str(e)}")
                self.disconnect()

    def _reader(self):
        buf = ""
        while self.running:
            try:
                if self.ser and self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting).decode(errors="ignore")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        self.signals.rx.emit(line.strip())
                time.sleep(0.01)
            except Exception as e:
                if self.running:
                    self._log(f"Read error: {str(e)}")
                    break

    # ================= PARSER =================
    def _parse(self, line):
        try:
            if "," in line:
                parts = line.split(",")
                if len(parts) >= 3:
                    v, i, p = map(float, parts[:3])
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
        self.btn_auto.clicked.connect(self.toggle_auto_connect)
        self.btn_rs.clicked.connect(lambda: self.send_cmd("rs"))
        self.btn_r.clicked.connect(lambda: self.send_cmd("r"))
        
        self.signals.rx.connect(self._on_rx)

    def _on_rx(self, line):
        self._log("RX: " + line)
        self._parse(line)

    def closeEvent(self, event):
        """Clean up on window close"""
        if self.auto_connecting:
            self.stop_auto_connect()
        if self.ser:
            self.disconnect()
        event.accept()


# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = RS485Monitor()
    win.show()
    sys.exit(app.exec())