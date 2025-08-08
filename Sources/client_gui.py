import ctypes
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import time
import threading
import sys
import os
import queue

from local_ntp.common import (
    load_settings,
    save_settings,
    discover_server,
    get_time_from_server,
)

class ClientGUI:
    CONFIG_FILE = "client_settings.json"
    def __init__(self, root):
        self.root = root
        self.root.title("CustoNTP Client")
        self._autorun_enabled = False
        self.log_queue = queue.Queue()
        self.create_widgets()
        self.load_settings()
        self.check_autorun_state()
        self.root.after(100, self._process_log_queue)

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        tk.Label(frame, text="IP сервера:").grid(row=0, column=0, sticky="e")
        self.server_ip_entry = tk.Entry(frame)
        self.server_ip_entry.grid(row=0, column=1, padx=5)

        self.copy_ip_btn = tk.Button(frame, text="Копировать IP", command=self.copy_ip)
        self.copy_ip_btn.grid(row=0, column=2, padx=2)

        self.find_server_btn = tk.Button(frame, text="Найти сервер", command=self.find_server)
        self.find_server_btn.grid(row=0, column=3, padx=2)

        tk.Label(frame, text="Порт:").grid(row=0, column=4, sticky="e")
        self.port_entry = tk.Entry(frame, width=6)
        self.port_entry.grid(row=0, column=5, padx=5)

        self.sync_btn = tk.Button(frame, text="Синхронизировать время", command=self.sync_time)
        self.sync_btn.grid(row=0, column=6, padx=5)

        self.autorun_btn = tk.Button(frame, text='Включить автозапуск', command=self.toggle_autorun)
        self.autorun_btn.grid(row=0, column=7, padx=5)

        self.log_text = scrolledtext.ScrolledText(self.root, width=90, height=15, state=tk.DISABLED)
        self.log_text.pack(padx=10, pady=10)

    def log(self, msg):
        self.log_queue.put(msg)

    def _process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(100, self._process_log_queue)

    def sync_time(self):
        server_ip = self.server_ip_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный порт!")
            return
        self.save_settings()
        threading.Thread(target=self._sync_time_thread, args=(server_ip, port), daemon=True).start()

    def _sync_time_thread(self, server_ip, port):
        try:
            server_time, rtt = get_time_from_server(server_ip, port)
            self.log(f"[CLIENT] Измеренный ping (RTT): {rtt*1000:.2f} мс")
            self.log(f"[CLIENT] Получено время: {server_time}")
                # Логика разбора времени с миллисекундами
                if '.' in server_time:
                    date_str, time_str = server_time.split(' ')
                    time_main, ms = time_str.split('.')
                    self.log(f"[CLIENT] Получено время с миллисекундами: {date_str} {time_main}.{ms}")
                else:
                    date_str, time_str = server_time.split(' ')
                    ms = '000'
                # Корректируем время на половину RTT (только для логов)
                from datetime import datetime, timedelta
                dt_format = '%Y-%m-%d %H:%M:%S.%f'
                if '.' in server_time:
                    dt = datetime.strptime(server_time, dt_format)
                else:
                    dt = datetime.strptime(server_time, '%Y-%m-%d %H:%M:%S')
                corrected_dt = dt + timedelta(seconds=rtt/2)
                self.log(f"[CLIENT] Время с учётом ping/2: {corrected_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                # Ждём половину RTT перед установкой времени
                self.log(f"[CLIENT] Ожидание {rtt/2:.4f} сек для учёта ping/2 перед установкой времени...")
                time.sleep(rtt/2)
                # Преобразуем дату из ГГГГ-ММ-ДД в ДД-ММ-ГГ
                y, m, d = date_str.split('-')
                date_for_win = f"{d}-{m}-{y[2:]}"
                try:
                    # Попытка установить время через WinAPI с миллисекундами (теперь сервер всегда шлёт UTC)
                    import ctypes
                    # НЕ переводим в UTC, сервер уже шлёт UTC
                    if '.' in server_time:
                        dt_utc = datetime.strptime(f"{date_str} {time_str}", dt_format)
                    else:
                        dt_utc = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
                    class SYSTEMTIME(ctypes.Structure):
                        _fields_ = [
                            ("wYear", ctypes.c_ushort),
                            ("wMonth", ctypes.c_ushort),
                            ("wDayOfWeek", ctypes.c_ushort),
                            ("wDay", ctypes.c_ushort),
                            ("wHour", ctypes.c_ushort),
                            ("wMinute", ctypes.c_ushort),
                            ("wSecond", ctypes.c_ushort),
                            ("wMilliseconds", ctypes.c_ushort),
                        ]
                    st = SYSTEMTIME()
                    st.wYear = dt_utc.year
                    st.wMonth = dt_utc.month
                    st.wDay = dt_utc.day
                    st.wHour = dt_utc.hour
                    st.wMinute = dt_utc.minute
                    st.wSecond = dt_utc.second
                    st.wMilliseconds = int(dt_utc.microsecond / 1000)
                    res = ctypes.windll.kernel32.SetSystemTime(ctypes.byref(st))
                    if res:
                        self.log(f"[CLIENT] Время установлено через WinAPI (UTC): {dt_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    else:
                        self.log(f"[CLIENT] Не удалось установить время через WinAPI. Код ошибки: {ctypes.GetLastError()}")
                except Exception as e:
                    self.log(f"[CLIENT] Ошибка при установке времени через WinAPI: {e}")
                # Также пробуем стандартный способ для совместимости
                try:
                    subprocess.run(f'date {date_for_win}', shell=True, check=True)
                    subprocess.run(f'time {time_str[:8]}', shell=True, check=True)  # только до секунд
                    self.log(f"[CLIENT] Время синхронизировано!")
                except Exception as e:
                    self.log(f"[CLIENT] Не удалось изменить время. Запустите программу от имени администратора! Ошибка: {e}")
        except Exception as e:
            self.log(f"[CLIENT] Ошибка: {e}")

    def copy_ip(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.server_ip_entry.get())
        self.log("[CLIENT] IP скопирован в буфер обмена.")

    def find_server(self):
        threading.Thread(target=self._find_server_thread, daemon=True).start()

    def _find_server_thread(self):
        self.log("[CLIENT] Поиск сервера...")
        try:
            port = int(self.port_entry.get())
        except ValueError:
            self.log("[CLIENT] Некорректный порт для поиска")
            return
        ip = None
        try:
            ip = discover_server(port)
        except Exception as e:
            self.log(f"[CLIENT] Сервер не найден: {e}")
            return
        if ip:
            self.server_ip_entry.delete(0, tk.END)
            self.server_ip_entry.insert(0, ip)
            self.log(f"[CLIENT] Сервер найден: {ip}")
            self.save_settings()
        else:
            self.log("[CLIENT] Сервер не найден")

    def save_settings(self):
        data = {
            "ip": self.server_ip_entry.get(),
            "port": self.port_entry.get(),
        }
        try:
            save_settings(self.CONFIG_FILE, data)
        except Exception as e:
            self.log(f"[CLIENT] Не удалось сохранить настройки: {e}")

    def load_settings(self):
        try:
            data = load_settings(self.CONFIG_FILE)
        except Exception:
            data = {}
        self.server_ip_entry.delete(0, tk.END)
        self.server_ip_entry.insert(0, data.get("ip", "127.0.0.1"))
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, data.get("port", "12345"))

    def toggle_autorun(self):
        try:
            import win32com.client
        except ImportError:
            messagebox.showerror('Ошибка', 'Для автозапуска требуется модуль pywin32. Установите его: pip install pywin32')
            return
        startup_dir = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_dir, 'CustoNTP Client.lnk')
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
            self.autorun_btn.config(text='Отключить автозапуск')
            messagebox.showinfo('Автозапуск', 'Автозапуск включён!')
        else:
            try:
                os.remove(shortcut_path)
                self._autorun_enabled = False
                self.autorun_btn.config(text='Включить автозапуск')
                messagebox.showinfo('Автозапуск', 'Автозапуск отключён!')
            except Exception as e:
                messagebox.showerror('Ошибка', f'Не удалось удалить ярлык автозапуска: {e}')

    def check_autorun_state(self):
        startup_dir = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_dir, 'CustoNTP Client.lnk')
        enabled = os.path.exists(shortcut_path)
        self._autorun_enabled = enabled
        if enabled:
            self.autorun_btn.config(text='Отключить автозапуск')
        else:
            self.autorun_btn.config(text='Включить автозапуск')

if __name__ == '__main__':
    root = tk.Tk()
    # Проверка прав администратора
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        is_admin = False
    if not is_admin:
        messagebox.showwarning('Внимание', 'Программа запущена без прав администратора!\nСинхронизация времени может не работать.')
    app = ClientGUI(root)
    root.mainloop()
