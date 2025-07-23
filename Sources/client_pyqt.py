import sys
import socket
import threading
import json
import os
import subprocess
import ctypes

from PyQt5 import QtWidgets, QtCore

class ClientGUI(QtWidgets.QWidget):
    CONFIG_FILE = 'client_settings.json'

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CustoNTP Client (PyQt)')
        self._autorun_enabled = False
        self._build_ui()
        self._load_settings()
        self._check_autorun_state()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QGridLayout()
        layout.addLayout(form_layout)

        form_layout.addWidget(QtWidgets.QLabel('IP сервера:'), 0, 0)
        self.server_ip = QtWidgets.QLineEdit()
        form_layout.addWidget(self.server_ip, 0, 1)
        self.copy_ip_btn = QtWidgets.QPushButton('Копировать IP')
        self.copy_ip_btn.clicked.connect(self.copy_ip)
        form_layout.addWidget(self.copy_ip_btn, 0, 2)
        self.find_btn = QtWidgets.QPushButton('Найти сервер')
        self.find_btn.clicked.connect(self.find_server)
        form_layout.addWidget(self.find_btn, 0, 3)

        form_layout.addWidget(QtWidgets.QLabel('Порт:'), 1, 0)
        self.port_edit = QtWidgets.QLineEdit()
        self.port_edit.setFixedWidth(60)
        form_layout.addWidget(self.port_edit, 1, 1)
        self.sync_btn = QtWidgets.QPushButton('Синхронизировать время')
        self.sync_btn.clicked.connect(self.sync_time)
        form_layout.addWidget(self.sync_btn, 1, 2, 1, 2)

        self.autorun_btn = QtWidgets.QPushButton('Включить автозапуск')
        self.autorun_btn.clicked.connect(self.toggle_autorun)
        form_layout.addWidget(self.autorun_btn, 2, 0, 1, 4)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def log(self, msg):
        self.log_box.append(msg)

    def sync_time(self):
        server_ip = self.server_ip.text()
        try:
            port = int(self.port_edit.text())
        except ValueError:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', 'Некорректный порт!')
            return
        self._save_settings()
        threading.Thread(target=self._sync_thread, args=(server_ip, port), daemon=True).start()

    def _sync_thread(self, server_ip, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                import time
                ping_start = time.time()
                s.connect((server_ip, port))
                ping_end = time.time()
                rtt = ping_end - ping_start
                self.log(f'[CLIENT] Измеренный ping (RTT): {rtt*1000:.2f} мс')
                data = s.recv(1024)
                server_time = data.decode('utf-8')
                self.log(f'[CLIENT] Получено время: {server_time}')
                date_str, time_str = server_time.split(' ')
                from datetime import datetime, timedelta
                dt_format = '%Y-%m-%d %H:%M:%S.%f'
                if '.' not in time_str:
                    dt = datetime.strptime(server_time, '%Y-%m-%d %H:%M:%S')
                else:
                    dt = datetime.strptime(server_time, dt_format)
                corrected_dt = dt + timedelta(seconds=rtt/2)
                self.log(f'[CLIENT] Время с учётом ping/2: {corrected_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}')
                time.sleep(rtt/2)
                y, m, d = date_str.split('-')
                date_for_win = f'{d}-{m}-{y[2:]}'
                try:
                    if '.' in server_time:
                        dt_utc = datetime.strptime(server_time, dt_format)
                    else:
                        dt_utc = datetime.strptime(server_time, '%Y-%m-%d %H:%M:%S')
                    class SYSTEMTIME(ctypes.Structure):
                        _fields_ = [
                            ('wYear', ctypes.c_ushort),
                            ('wMonth', ctypes.c_ushort),
                            ('wDayOfWeek', ctypes.c_ushort),
                            ('wDay', ctypes.c_ushort),
                            ('wHour', ctypes.c_ushort),
                            ('wMinute', ctypes.c_ushort),
                            ('wSecond', ctypes.c_ushort),
                            ('wMilliseconds', ctypes.c_ushort),
                        ]
                    st = SYSTEMTIME()
                    st.wYear = dt_utc.year
                    st.wMonth = dt_utc.month
                    st.wDay = dt_utc.day
                    st.wHour = dt_utc.hour
                    st.wMinute = dt_utc.minute
                    st.wSecond = dt_utc.second
                    st.wMilliseconds = int(dt_utc.microsecond/1000)
                    res = ctypes.windll.kernel32.SetSystemTime(ctypes.byref(st))
                    if res:
                        self.log('[CLIENT] Время установлено через WinAPI')
                    else:
                        self.log(f'[CLIENT] Не удалось установить время через WinAPI. Код ошибки: {ctypes.GetLastError()}')
                except Exception as e:
                    self.log(f'[CLIENT] Ошибка при установке времени через WinAPI: {e}')
                try:
                    subprocess.run(f'date {date_for_win}', shell=True, check=True)
                    subprocess.run(f'time {time_str[:8]}', shell=True, check=True)
                    self.log('[CLIENT] Время синхронизировано!')
                except Exception as e:
                    self.log(f'[CLIENT] Не удалось изменить время. Запустите программу от имени администратора! Ошибка: {e}')
        except Exception as e:
            self.log(f'[CLIENT] Ошибка: {e}')

    def copy_ip(self):
        cb = QtWidgets.QApplication.clipboard()
        cb.setText(self.server_ip.text())
        self.log('[CLIENT] IP скопирован в буфер обмена.')

    def find_server(self):
        threading.Thread(target=self._find_thread, daemon=True).start()

    def _find_thread(self):
        self.log('[CLIENT] Поиск сервера...')
        try:
            port = int(self.port_edit.text())
        except ValueError:
            self.log('[CLIENT] Некорректный порт для поиска')
            return
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(2)
                s.sendto(b'CUSTONTP_DISCOVER', ('<broadcast>', port))
                data, addr = s.recvfrom(1024)
                if data == b'CUSTONTP_RESPONSE':
                    self.server_ip.setText(addr[0])
                    self.log(f'[CLIENT] Сервер найден: {addr[0]}')
                    self._save_settings()
                    return
        except Exception as e:
            self.log(f'[CLIENT] Сервер не найден: {e}')

    def _save_settings(self):
        data = {
            'ip': self.server_ip.text(),
            'port': self.port_edit.text()
        }
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            self.log(f'[CLIENT] Не удалось сохранить настройки: {e}')

    def _load_settings(self):
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.server_ip.setText(data.get('ip', '127.0.0.1'))
                self.port_edit.setText(data.get('port', '12345'))
        except Exception:
            self.server_ip.setText('127.0.0.1')
            self.port_edit.setText('12345')

    def toggle_autorun(self):
        try:
            import win32com.client
        except ImportError:
            QtWidgets.QMessageBox.critical(self, 'Ошибка', 'Для автозапуска требуется pywin32')
            return
        startup = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup, 'CustoNTP Client.lnk')
        script_path = os.path.abspath(sys.argv[0])
        if not self._autorun_enabled:
            shell = win32com.client.Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{script_path}"'
            shortcut.WorkingDirectory = os.path.dirname(script_path)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            self._autorun_enabled = True
            self.autorun_btn.setText('Отключить автозапуск')
            QtWidgets.QMessageBox.information(self, 'Автозапуск', 'Автозапуск включён!')
        else:
            try:
                os.remove(shortcut_path)
                self._autorun_enabled = False
                self.autorun_btn.setText('Включить автозапуск')
                QtWidgets.QMessageBox.information(self, 'Автозапуск', 'Автозапуск отключён!')
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, 'Ошибка', f'Не удалось удалить ярлык автозапуска: {e}')

    def _check_autorun_state(self):
        startup = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup, 'CustoNTP Client.lnk')
        self._autorun_enabled = os.path.exists(shortcut_path)
        if self._autorun_enabled:
            self.autorun_btn.setText('Отключить автозапуск')
        else:
            self.autorun_btn.setText('Включить автозапуск')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = ClientGUI()
    gui.show()
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False
    if not is_admin:
        QtWidgets.QMessageBox.warning(gui, 'Внимание', 'Программа запущена без прав администратора!\nСинхронизация времени может не работать.')
    sys.exit(app.exec_())
