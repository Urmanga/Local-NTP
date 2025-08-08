import ctypes
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import sys
import os

from local_ntp.common import (
    load_settings,
    save_settings,
    discover_server,
    get_time_from_server,
)
from local_ntp.sync import sync_time

class ClientGUI:
    CONFIG_FILE = "client_settings.json"
    def __init__(self, root):
        self.root = root
        self.root.title("CustoNTP Client")
        self._autorun_enabled = False
        self.create_widgets()
        self.load_settings()
        self.check_autorun_state()

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
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

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
            sync_time(server_time, rtt, self.log)
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
