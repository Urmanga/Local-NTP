"""Utilities for synchronizing local time with a server."""

import subprocess
import ctypes
import time
from datetime import datetime, timedelta


def sync_time(server_time: str, rtt: float, log_callback):
    """Parse, adjust and set system time based on server response.

    Args:
        server_time: Time string received from the server in the format
            ``YYYY-MM-DD HH:MM:SS`` with optional milliseconds.
        rtt: Round trip time in seconds.
        log_callback: Callable used for logging messages.
    """

    if "." in server_time:
        date_str, time_str = server_time.split(" ")
        time_main, ms = time_str.split(".")
        log_callback(
            f"[CLIENT] Получено время с миллисекундами: {date_str} {time_main}.{ms}"
        )
    else:
        date_str, time_str = server_time.split(" ")
        ms = "000"

    dt_format = "%Y-%m-%d %H:%M:%S.%f"
    if "." in server_time:
        dt = datetime.strptime(server_time, dt_format)
    else:
        dt = datetime.strptime(server_time, "%Y-%m-%d %H:%M:%S")

    corrected_dt = dt + timedelta(seconds=rtt / 2)
    log_callback(
        f"[CLIENT] Время с учётом ping/2: {corrected_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
    )
    log_callback(
        f"[CLIENT] Ожидание {rtt/2:.4f} сек для учёта ping/2 перед установкой времени..."
    )
    time.sleep(rtt / 2)

    y, m, d = date_str.split("-")
    date_for_win = f"{d}-{m}-{y[2:]}"

    try:
        if "." in server_time:
            dt_utc = datetime.strptime(f"{date_str} {time_str}", dt_format)
        else:
            dt_utc = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

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
            log_callback(
                f"[CLIENT] Время установлено через WinAPI (UTC): {dt_utc.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}"
            )
        else:
            log_callback(
                f"[CLIENT] Не удалось установить время через WinAPI. Код ошибки: {ctypes.GetLastError()}"
            )
    except Exception as e:
        log_callback(f"[CLIENT] Ошибка при установке времени через WinAPI: {e}")

    try:
        subprocess.run(f"date {date_for_win}", shell=True, check=True)
        subprocess.run(f"time {time_str[:8]}", shell=True, check=True)
        log_callback("[CLIENT] Время синхронизировано!")
    except Exception as e:
        log_callback(
            "[CLIENT] Не удалось изменить время. Запустите программу от имени администратора! Ошибка: {e}"
        )

