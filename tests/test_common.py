import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from local_ntp.common import current_utc_time, save_settings, load_settings

def test_time_format():
    ts = current_utc_time()
    assert 'T' not in ts  # space separator
    date, time_str = ts.split(' ')
    assert len(date.split('-')) == 3
    assert '.' in time_str

def test_settings_rw(tmp_path):
    cfg = tmp_path/'cfg.json'
    data = {'ip': '1.2.3.4', 'port': '9999'}
    save_settings(cfg, data)
    loaded = load_settings(cfg)
    assert loaded == data
