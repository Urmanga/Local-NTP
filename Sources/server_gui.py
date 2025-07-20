import threading
import socket
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox

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
        self.thread = threading.Thread(target=self.run_server, daemon=True)
        self.thread.start()
        self.udp_running = True
        self.udp_thread = threading.Thread(target=self.udp_broadcast_listener, daemon=True)
        self.udp_thread.start()
        self.log_callback(f"[SERVER] Сервер запущен на порту {port}")

    def stop(self):
        self.running = False
        self.udp_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.log_callback(f"[SERVER] Ошибка при закрытии сокета: {e}")
            self.sock = None  # Обнуляем, чтобы не было повторного закрытия
        self.log_callback("[SERVER] Сервер остановлен")

    def run_server(self):
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
                    self.log_callback(f"[SERVER] Ошибка: {e}")
                    break
                with conn:
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.sendall(now.encode('utf-8'))
                    self.log_callback(f"[SERVER] Подключение от {addr}, отправлено время: {now}")

    def udp_broadcast_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_sock.bind(('', self.port))
            while self.udp_running:
                try:
                    udp_sock.settimeout(1.0)
                    data, addr = udp_sock.recvfrom(1024)
                    if data == b'CUSTONTP_DISCOVER':
                        udp_sock.sendto(b'CUSTONTP_RESPONSE', addr)
                        self.log_callback(f"[SERVER] Получен broadcast-запрос от {addr}, отправлен ответ")
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log_callback(f"[SERVER][UDP] Ошибка: {e}")
                    break

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CustoNTP Server")
        self.server = None
        self.create_widgets()
        self.is_running = False

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        tk.Label(frame, text="Порт:").grid(row=0, column=0, sticky="e")
        self.port_entry = tk.Entry(frame)
        self.port_entry.insert(0, "12345")
        self.port_entry.grid(row=0, column=1, padx=5)

        self.start_btn = tk.Button(frame, text="Запустить сервер", command=self.start_server)
        self.start_btn.grid(row=0, column=2, padx=5)
        self.stop_btn = tk.Button(frame, text="Остановить сервер", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=3, padx=5)

        self.log_text = scrolledtext.ScrolledText(self.root, width=70, height=20, state=tk.DISABLED)
        self.log_text.pack(padx=10, pady=10)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_server(self):
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный порт!")
            return
        self.server = TimeServer(self.log)
        self.server.start(port)
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.DISABLED)

    def stop_server(self):
        if self.server:
            self.server.stop()
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_server(), root.destroy()))
    root.mainloop() 