import sys
import socket
import threading
from PyQt5 import QtWidgets
from local_ntp.common import current_utc_time

class TimeServer:
    def __init__(self, log_callback):
        self.running = False
        self.thread = None
        self.sock = None
        self.log_callback = log_callback
        self.port = 12345
        self.udp_thread = None
        self.udp_running = False

    def start(self, port):
        self.running = True
        self.port = port
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        self.udp_running = True
        self.udp_thread = threading.Thread(target=self._udp_listener, daemon=True)
        self.udp_thread.start()
        self.log_callback(f'[SERVER] Сервер запущен на порту {port}')

    def stop(self):
        self.running = False
        self.udp_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.log_callback(f'[SERVER] Ошибка при закрытии сокета: {e}')
            self.sock = None
        self.log_callback('[SERVER] Сервер остановлен')

    def _run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.sock = s
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', self.port))
            s.listen()
            while self.running:
                try:
                    s.settimeout(1.0)
                    conn, addr = s.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_callback(f'[SERVER] Ошибка: {e}')
                    break
                with conn:
                    now = current_utc_time()
                    conn.sendall(now.encode('utf-8'))
                    self.log_callback(f'[SERVER] Подключение от {addr}, отправлено UTC-время: {now}')

    def _udp_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp.bind(('', self.port))
            while self.udp_running:
                try:
                    udp.settimeout(1.0)
                    data, addr = udp.recvfrom(1024)
                    if data == b'CUSTONTP_DISCOVER':
                        udp.sendto(b'CUSTONTP_RESPONSE', addr)
                        self.log_callback(f'[SERVER] Получен broadcast-запрос от {addr}, отправлен ответ')
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_callback(f'[SERVER][UDP] Ошибка: {e}')
                    break

class ServerGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CustoNTP Server (PyQt)')
        self.server = None
        self.is_running = False
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QGridLayout()
        layout.addLayout(form_layout)

        form_layout.addWidget(QtWidgets.QLabel('Порт:'), 0, 0)
        self.port_edit = QtWidgets.QLineEdit('12345')
        form_layout.addWidget(self.port_edit, 0, 1)
        self.start_btn = QtWidgets.QPushButton('Запустить сервер')
        self.start_btn.clicked.connect(self.start_server)
        form_layout.addWidget(self.start_btn, 0, 2)
        self.stop_btn = QtWidgets.QPushButton('Остановить сервер')
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        form_layout.addWidget(self.stop_btn, 0, 3)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def log(self, msg):
        self.log_box.append(msg)

    def start_server(self):
        try:
            port = int(self.port_edit.text())
        except ValueError:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', 'Некорректный порт!')
            return
        self.server = TimeServer(self.log)
        self.server.start(port)
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.port_edit.setEnabled(False)

    def stop_server(self):
        if self.server:
            self.server.stop()
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.port_edit.setEnabled(True)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = ServerGUI()
    gui.show()
    app.aboutToQuit.connect(lambda: gui.stop_server())
    sys.exit(app.exec_())
