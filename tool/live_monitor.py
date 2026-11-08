"""Live response-time monitor for JMeter result CSV files.

    python live_monitor.py [PATH]                 PATH = a CSV file or a folder (newest CSV is used)
    python live_monitor.py --dir C:\\path\\to\\report\\run1 [--file NAME]

Without PATH the page starts idle: type a path in the box at the top right and press
"Start tracking". Reads the standard JMeter CSV columns (timeStamp, elapsed, label,
responseCode, success, ...). Serves a Response Time Graph style page on http://localhost:8765.
Standard library only.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
PREFERRED = ('response_graph', 'view_result_tree', 'agg_report', 'summary')
TS_FORMATS = ('%Y/%m/%d %H:%M:%S.%f', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
              '%m/%d/%y %H:%M:%S', '%d/%m/%y %H:%M:%S')


def parse_ts(text):
    """JMeter writes epoch ms by default; also accept the formatted timestamps jmeter.properties can produce."""
    try:
        return int(float(text))
    except ValueError:
        pass
    for fmt in TS_FORMATS:
        try:
            return int(datetime.strptime(text, fmt).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(text)


class Tail:
    """Reads a CSV that another process may still be appending to."""

    def __init__(self, path, thresholds, default_thr):
        self.path = path
        self.thresholds = thresholds
        self.default_thr = default_thr
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.offset = 0
        self.head = b''
        self.cols = None
        self.samples = []  # (ts_ms, elapsed, label, code, ok, message)

    def threshold(self, label):
        low = label.lower()
        for key, ms in self.thresholds:
            if key in low:
                return ms
        return self.default_thr

    def poll(self):
        try:
            f = open(self.path, 'rb')
        except OSError:
            return
        with f, self.lock:
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
            head = f.read(256)
            # file was rewritten (same name, new run): start over
            if size < self.offset or (self.head and not head.startswith(self.head[:len(head)])):
                self.reset()
            if len(head) > len(self.head):
                self.head = head
            f.seek(self.offset)
            data = f.read()
            cut = data.rfind(b'\n')
            if cut < 0:
                return
            chunk = data[:cut + 1]
            text = chunk.decode('utf-8-sig', errors='replace')
            if text.count('"') % 2:  # record with a quoted newline is still being written
                return
            self.offset += len(chunk)
            for row in csv.reader(io.StringIO(text)):
                if not row:
                    continue
                if self.cols is None:
                    self.cols = {name.strip(): i for i, name in enumerate(row)}
                    continue
                try:
                    g = lambda name: row[self.cols[name]] if name in self.cols and self.cols[name] < len(row) else ''
                    self.samples.append((parse_ts(g('timeStamp')), int(float(g('elapsed'))), g('label'),
                                         g('responseCode'), g('success').strip().lower() == 'true',
                                         g('failureMessage') or g('responseMessage')))
                except (KeyError, ValueError):
                    continue

    def snapshot(self, interval, t_from=None, t_to=None):
        """t_from / t_to (epoch ms, None = open) pick the samples used for the per-request statistics."""
        with self.lock:
            samples = list(self.samples)
        out = empty(interval)
        out['file'] = self.path.name
        out['samples'] = len(samples)
        out['rangeFrom'], out['rangeTo'] = t_from, t_to
        if not samples:
            return out
        out['errorsTotal'] = sum(1 for s in samples if not s[4])
        now = out['now']
        t_max = max(s[0] for s in samples)
        out['lastAge'] = round((now - t_max) / 1000)
        out['first'], out['last'] = min(s[0] for s in samples), t_max

        by_label = {}  # insertion order = order of first appearance
        for s in samples:
            by_label.setdefault(s[2], []).append(s)

        shown = samples
        step = interval * 1000
        first, last = min(s[0] for s in shown) // step, t_max // step
        agg = {}
        for ts, el, label, *_ in shown:
            cell = agg.setdefault((ts // step, label), [0, 0])
            cell[0] += el
            cell[1] += 1
        idx = range(first, last + 1)
        out['start'] = first * step
        out['buckets'] = [time.strftime('%H:%M:%S', time.localtime(b * step / 1000)) for b in idx]
        for label in by_label:
            data = []
            for b in idx:
                cell = agg.get((b, label))
                data.append(round(cell[0] / cell[1]) if cell else None)
            out['series'].append({'label': label, 'data': data, 'threshold': self.threshold(label)})

        out['errors'] = [{'ts': s[0], 'label': s[2], 'elapsed': s[1], 'code': s[3] or '(none)'} for s in shown if not s[4]][-2000:]

        in_range = [s for s in samples if (t_from is None or s[0] >= t_from) and (t_to is None or s[0] <= t_to)]
        stat_rows = {}
        for s in in_range:
            stat_rows.setdefault(s[2], []).append(s)
        for label, rows in stat_rows.items():
            times = sorted(s[1] for s in rows)
            pct = lambda p: times[min(len(times) - 1, int(len(times) * p))]  # same rule as JMeter's aggregate report
            out['stats'].append({
                'label': label, 'count': len(rows), 'errors': sum(1 for s in rows if not s[4]),
                'min': times[0], 'avg': round(sum(times) / len(times)), 'median': pct(0.5), 'p90': pct(0.9), 'p95': pct(0.95),
                'p99': pct(0.99), 'max': times[-1], 'threshold': self.threshold(label)})

        for ts, el, label, code, ok, msg in reversed(samples):
            slow = el > self.threshold(label)
            if ok and not slow:
                continue
            out['alerts'].append({'ts': ts, 'time': time.strftime('%H:%M:%S', time.localtime(ts / 1000)),
                                  'label': label, 'kind': 'ERROR' if not ok else 'SLOW',
                                  'elapsed': el, 'code': code, 'message': msg[:300]})
            if len(out['alerts']) >= 1000:
                break
        return out


def empty(interval):
    return {'file': '', 'samples': 0, 'interval': interval, 'now': int(time.time() * 1000), 'lastAge': None,
            'buckets': [], 'series': [], 'stats': [], 'alerts': [], 'errors': [], 'errorsTotal': 0,
            'rangeFrom': None, 'rangeTo': None}


def pick_file(folder, name=None):
    if name:
        return folder / name
    files = [f for f in folder.glob('*.csv') if f.is_file()]
    for key in PREFERRED:
        for f in sorted(files):
            if key in f.name:
                return f
    # a folder of runs (e.g. one CSV per run): take the newest
    return max(files, key=lambda f: f.stat().st_mtime) if files else folder / 'missing.csv'


def resolve(text):
    text = (text or '').strip().strip('"').strip("'").strip()
    if not text:
        raise ValueError('Enter a CSV file path or a folder')
    p = Path(text).expanduser()
    if p.is_dir():
        f = pick_file(p)
        if not f.is_file():
            raise ValueError('No .csv file in that folder')
        return f
    if p.is_file():
        return p
    raise ValueError('Not found: ' + text)


_dialog = threading.Lock()
_last_dir = [None]


_DIALOG = (
    "import sys, tkinter\n"
    "from tkinter import filedialog\n"
    "root = tkinter.Tk(); root.withdraw(); root.attributes('-topmost', True)\n"
    "print(filedialog.askopenfilename(parent=root, title='Select the CSV to track',"
    " initialdir=sys.argv[1] or None,"
    " filetypes=[('JMeter results', '*.csv *.jtl'), ('All files', '*.*')]))\n")


def browse(current):
    """Native 'open file' dialog on the machine running this script. It runs in a child process, because Tk must
    own the main thread (on macOS it can abort the whole process otherwise) and has no display on a headless box."""
    if not _dialog.acquire(blocking=False):
        raise ValueError('A file dialog is already open')
    try:
        text = os.path.expanduser((current or '').strip().strip('"').strip("'"))
        start = Path(text) if text else None
        initial = (start.parent if start.is_file() else start if start.is_dir() else _last_dir[0]) if start else _last_dir[0]
        try:
            r = subprocess.run([sys.executable, '-c', _DIALOG, str(initial) if initial else ''],
                               capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('cannot open the file dialog, paste the path instead')
    finally:
        _dialog.release()
    if r.returncode != 0:
        raise ValueError('file dialog not available (tkinter or a display is missing), paste the path instead')
    chosen = r.stdout.strip()
    if not chosen:
        return ''
    chosen = os.path.normpath(chosen)  # tk gives forward slashes, also for \\server\share
    _last_dir[0] = Path(chosen).parent
    return chosen


class Monitor:
    def __init__(self, thresholds, default_thr):
        self.thresholds = thresholds
        self.default_thr = default_thr
        self.lock = threading.Lock()
        self.tail = None
        self.tracking = False

    def start(self, text):
        tail = Tail(resolve(text), self.thresholds, self.default_thr)
        tail.poll()
        with self.lock:
            self.tail, self.tracking = tail, True
        print('tracking', tail.path)

    def stop(self):
        with self.lock:
            self.tracking = False
        print('stopped')

    def data(self, interval, t_from=None, t_to=None):
        with self.lock:
            tail, tracking = self.tail, self.tracking
        if tail is None:
            out = empty(interval)
            out['path'] = ''
        else:
            if tracking:
                tail.poll()
            out = tail.snapshot(interval, t_from, t_to)
            out['path'] = str(tail.path)
        out['tracking'] = tracking
        return out


def make_handler(monitor):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, obj, code=200):
            self.send(code, json.dumps(obj).encode(), 'application/json')

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/':
                self.send(200, (HERE / 'live_monitor.html').read_bytes(), 'text/html; charset=utf-8')
            elif url.path == '/api/data':
                q = parse_qs(url.query)
                interval = max(1, int(q.get('interval', ['10'])[0]))
                num = lambda key: int(q[key][0]) if q.get(key, [''])[0].lstrip('-').isdigit() else None
                self.send_json(monitor.data(interval, num('from'), num('to')))
            else:
                self.send(404, b'not found', 'text/plain')

        def do_POST(self):
            url = urlparse(self.path)
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0)) or 0) or b'{}')
            except ValueError:
                body = {}
            if url.path == '/api/track':
                try:
                    monitor.start(body.get('path', ''))
                except ValueError as e:
                    self.send_json({'error': str(e)}, 400)
                    return
                self.send_json({'ok': True})
            elif url.path == '/api/browse':
                try:
                    self.send_json({'path': browse(body.get('path', ''))})
                except ValueError as e:
                    self.send_json({'error': str(e)}, 400)
            elif url.path == '/api/stop':
                monitor.stop()
                self.send_json({'ok': True})
            else:
                self.send(404, b'not found', 'text/plain')

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path', nargs='?', help='CSV file, or a folder (newest CSV is used); starts tracking at once')
    ap.add_argument('--dir', help='folder holding the listener CSV files (same as PATH for a folder)')
    ap.add_argument('--file', help='CSV file name inside --dir (default: auto)')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--default-thr', type=int, default=10000, help='slow threshold in ms (default 10000)')
    ap.add_argument('--thr', action='append', default=[],
                    metavar='TEXT=MS', help='slow threshold for labels containing TEXT, e.g. login=3000 (repeatable)')
    ap.add_argument('--no-browser', action='store_true')
    a = ap.parse_args()

    thresholds = []
    for item in a.thr:
        key, _, ms = item.rpartition('=')
        thresholds.append((key.strip().lower(), int(ms)))

    monitor = Monitor(thresholds, a.default_thr)
    start = a.path or (str(pick_file(Path(a.dir), a.file)) if a.dir else None)
    if start:
        try:
            monitor.start(start)
        except ValueError as e:
            print('not tracking:', e)

    server = ThreadingHTTPServer(('127.0.0.1', a.port), make_handler(monitor))
    url = 'http://localhost:%d' % a.port
    print('open', url, '(Ctrl+C to stop)')
    headless = sys.platform.startswith('linux') and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    if not a.no_browser and not headless:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
