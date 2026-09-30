from __future__ import annotations
import os
os.environ.setdefault("MPLBACKEND", "Agg")

import json, mimetypes, tempfile, threading, urllib.parse, uuid, webbrowser
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

from src.workspace import build_workspace
from src.agent_v2 import answer

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / 'data'
OUTPUTS = ROOT / 'outputs'
TEMPLATE = ROOT / 'templates' / 'index.html'
UP = ROOT / '.runtime_uploads'
UP.mkdir(exist_ok=True)

STATE = {'ws': None, 'dataset': 'Vireo Audio · Support Tickets Set C', 'mode': 'default', 'error': None}
JOBS = {}
JOBS_LOCK = threading.Lock()
ANALYSIS_LOCK = threading.Lock()
MAX = 120 * 1024 * 1024


def safe(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    if isinstance(v, pd.Timestamp): return v.isoformat()
    try:
        if pd.isna(v): return None
    except Exception:
        pass
    return v


def records(df, n=250):
    return [{k: safe(v) for k, v in r.items()} for r in df.head(n).to_dict('records')]


def set_job(job_id, **changes):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(changes)


def progress_for(job_id):
    def cb(stage, percent, detail):
        set_job(job_id, stage=stage, percent=percent, detail=detail, status='running')
    return cb


def load_default():
    STATE.update(ws=build_workspace(DEFAULT, OUTPUTS), dataset='Vireo Audio · Support Tickets Set C', mode='default', error=None)


def summary():
    ws = STATE['ws']
    if not ws:
        return {'ready': False, 'error': STATE['error']}
    f, a, ai, adv = ws['finance'], ws['audit'], ws['ai'], ws['advanced']
    return {
        'ready': True,
        'dataset_name': STATE['dataset'],
        'mode': STATE['mode'],
        'metrics': f['metrics'],
        'audit': a['summary'],
        'ai': ai['metrics'],
        'monthly': records(f['monthly'], 100),
        'reasons': records(f['focus_reason'], 30),
        'agents': records(f['focus_agent'], 50),
        'exceptions': records(f['focus_exceptions'].sort_values('dual_remedy_value_at_risk', ascending=False), 300),
        'ai_review': records(ai['review'], 300),
        'products': records(adv['product'], 50),
        'lots': records(adv['lots'], 80),
        'channels': records(adv['channel'], 20),
        'teams': records(adv['team'], 30),
        'reason_drivers': records(adv['reason_drivers'], 30),
        'quarter_compare': adv['quarter_compare'],
        'data_quality': records(adv['data_quality'], 20),
        'source_files': {k: Path(v).name for k, v in ws['pack'].source_files.items()},
        'downloads': [p.name for p in sorted(OUTPUTS.iterdir()) if p.is_file() and not p.name.startswith('.')],
    }


def clean(n):
    return Path(n or 'file.csv').name.replace('..', '_')


def run_custom_job(job_id, folder, dataset_name):
    try:
        with ANALYSIS_LOCK:
            set_job(job_id, status='running', stage='schema', percent=4, detail='Starting analysis on the uploaded support pack')
            ws = build_workspace(folder, OUTPUTS, progress_for(job_id))
            STATE.update(ws=ws, dataset=dataset_name, mode='custom', error=None)
            set_job(job_id, status='done', stage='complete', percent=100, detail='Analysis complete — workspace switched successfully')
    except Exception as e:
        set_job(job_id, status='error', stage='error', detail=str(e), error=str(e))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def j(self, x, status=200):
        b = json.dumps(x, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get('Content-Length', '0') or 0)
        return json.loads((self.rfile.read(n) or b'{}').decode())

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == '/':
            b = TEMPLATE.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        if p == '/api/summary':
            return self.j(summary())
        if p.startswith('/api/job/'):
            job_id = clean(p.split('/')[-1])
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id, {}))
            if not job:
                return self.j({'ok': False, 'error': 'Analysis job not found.'}, 404)
            return self.j({'ok': True, **job})
        if p.startswith('/download/'):
            t = OUTPUTS / clean(urllib.parse.unquote(p[10:]))
            if not t.exists():
                return self.send_error(404)
            b = t.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mimetypes.guess_type(t.name)[0] or 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{t.name}"')
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.send_error(404)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        try:
            if p == '/api/ask':
                return self.j({'ok': True, **answer(self.body().get('question', ''), STATE['ws'])})
            if p == '/api/reset':
                load_default()
                return self.j({'ok': True, 'summary': summary()})
            if p == '/api/upload':
                n = int(self.headers.get('Content-Length', '0') or 0)
                if n > MAX:
                    return self.j({'ok': False, 'error': 'Upload exceeds 120 MB.'}, 413)
                ct = self.headers.get('Content-Type', '')
                raw = self.rfile.read(n)
                env = (f'Content-Type: {ct}\r\nMIME-Version: 1.0\r\n\r\n').encode() + raw
                msg = BytesParser(policy=email_policy).parsebytes(env)
                d = Path(tempfile.mkdtemp(prefix='pack_', dir=UP))
                name = 'Custom support pack'
                saved = 0
                for part in msg.iter_parts():
                    field = part.get_param('name', header='content-disposition')
                    fn = part.get_filename()
                    payload = part.get_payload(decode=True) or b''
                    if field == 'dataset_name' and not fn:
                        name = payload.decode(errors='replace').strip()[:80] or name
                    elif field == 'files' and fn and fn.lower().endswith('.csv'):
                        (d / clean(fn)).write_bytes(payload)
                        saved += 1
                if saved < 5:
                    return self.j({'ok': False, 'error': f'Received {saved} CSVs; upload all five support-pack CSVs.'}, 400)
                job_id = uuid.uuid4().hex[:12]
                with JOBS_LOCK:
                    JOBS[job_id] = {
                        'status': 'queued', 'stage': 'queued', 'percent': 1,
                        'detail': f'{saved} CSVs received. Preparing the analysis pipeline.',
                        'dataset_name': name, 'files_received': saved,
                    }
                threading.Thread(target=run_custom_job, args=(job_id, d, name), daemon=True).start()
                return self.j({'ok': True, 'job_id': job_id, 'files_received': saved})
        except Exception as e:
            return self.j({'ok': False, 'error': str(e)}, 400)
        self.send_error(404)


def main():
    try:
        load_default()
    except Exception as e:
        STATE.update(ws=None, error=str(e))
    url = 'http://127.0.0.1:8765'
    threading.Timer(1, lambda: webbrowser.open(url)).start()
    print('\nVIREO REFUND ANALYST AI\nWorkspace:', url, '\nPress Ctrl+C to stop.\n')
    s = ThreadingHTTPServer(('127.0.0.1', 8765), H)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        s.server_close()


if __name__ == '__main__':
    main()
