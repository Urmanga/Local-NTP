# 🕒 CustoNTP — Кастомный NTP-сервер и клиент с GUI

Простое приложение для синхронизации времени между компьютерами в локальной сети. Включает удобные графические интерфейсы для сервера и клиента.

---

## 🚀 Возможности

- **GUI-клиент** (client_gui.py / client_pyqt.py / client_gui.exe):
  - Синхронизация времени с сервером по сети
  - Автоматический поиск сервера в локальной сети
  - Сохранение и автозагрузка последнего IP и порта
  - Копирование IP одним кликом
  - Автозапуск клиента при старте Windows (опционально)
  - Поддержка запуска от администратора для смены времени
  - Логи событий прямо в окне

- **GUI-сервер** (server_gui.py / server_pyqt.py / server_gui.exe):
  - Запуск и остановка сервера одной кнопкой
  - Выбор порта
  - Просмотр логов подключений и событий
  - Автоматический ответ на broadcast-запросы для поиска серверов клиентами

---

## 🖥️ Как запустить

### 1. Запуск через Python (для теста)

- **Клиент:**
  1. Запусти ``python client_gui.py`` или ``python client_pyqt.py``
  2. Или `../run_client_pyqt.bat`
- **Сервер:**
  1. Запусти ``python server_gui.py`` или ``python server_pyqt.py``
  2. Или `../run_server_pyqt.bat`

> ⚠️ Для смены времени на клиенте запускать от имени администратора!

### 2. Запуск exe-файлов

- После сборки через PyInstaller запускай `client_gui.exe` и `server_gui.exe` из папки `dist`.
- Для автозапуска и смены времени — запускать от имени администратора.

---

## 🛠️ Сборка exe-файлов

1. Установи зависимости:
   ```sh
   pip install pyinstaller pywin32 PyQt5
   ```
2. Собери exe:
   ```sh
   pyinstaller --onefile --noconsole --collect-all pywin32 --collect-all win32com --hidden-import=win32com --hidden-import=win32com.client --hidden-import=win32api --hidden-import=win32con client_gui.py
   pyinstaller --onefile --noconsole client_pyqt.py
   pyinstaller --onefile --noconsole server_gui.py
   pyinstaller --onefile --noconsole server_pyqt.py
   ```
3. Готовые файлы будут в папке `dist`.

---

## 🌐 Как работает автопоиск сервера

Клиент рассылает broadcast-запрос по сети, сервер отвечает, и IP сервера автоматически подставляется в поле клиента.

---

## 📦 Структура проекта

```
client_gui.py         # GUI-клиент
client_pyqt.py        # GUI-клиент (PyQt)
server_gui.py         # GUI-сервер
server_pyqt.py        # GUI-сервер (PyQt)
run_client_pyqt.bat   # Батник для клиента PyQt
run_server_pyqt.bat   # Батник для сервера PyQt
```

---

## 💡 Примечания

- Для смены времени на клиенте нужны права администратора.
- Для работы автозапуска pywin32 должен быть включён в exe (см. инструкцию по сборке).
- Если клиент не может найти сервер — проверьте брандмауэр и сетевые настройки.

---

## 📝 Лицензия

MIT 
