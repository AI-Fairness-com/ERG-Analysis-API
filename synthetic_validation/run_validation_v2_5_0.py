"""Run the v2.5.0 synthetic validation set against the ERG Analysis API.

Posts every CSV in synthetic_validation/v2_5_0/ to the API, compares each
reply with manifest.json, and writes results.csv and a PASS/FAIL summary.

Usage (from the repository root, with the server running):
    cd api && python erg_server.py          # in a second terminal
    python synthetic_validation/run_validation_v2_5_0.py
    python synthetic_validation/run_validation_v2_5_0.py --url https://erg-analysis-api-1.onrender.com
    python synthetic_validation/run_validation_v2_5_0.py --local   # no server: calls the app directly
"""
import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / 'synthetic_validation' / 'v2_5_0'
COLOURS = {'GREEN', 'AMBER', 'RED', 'ATYPICAL DIRECTION'}
# Chapter 2, Table 2.3: (Pass at or above, Fail below)
SNR_TABLE = {'contact_lens': (8.0, 4.0), 'gold_foil': (6.0, 3.0),
             'dtl_fiber': (4.0, 2.5), 'skin': (3.0, 2.0)}


def book_snr_status(electrode, snr):
    pass_at, fail_below = SNR_TABLE[electrode]
    return 'PASS' if snr >= pass_at else ('WARNING' if snr >= fail_below else 'FAIL')


def poster(url, local):
    if local:
        import contextlib
        sys.path.insert(0, str(ROOT / 'api'))
        with contextlib.redirect_stdout(io.StringIO()):
            import erg_server
        client = erg_server.app.test_client()

        def post(form, path):
            data = dict(form, file=(open(path, 'rb'), path.name))
            r = client.post('/api/v1/analyse', data=data,
                            content_type='multipart/form-data')
            return r.status_code, r.get_json()
        return post
    import requests

    def post(form, path):
        with open(path, 'rb') as f:
            r = requests.post(url.rstrip('/') + '/api/v1/analyse', data=form,
                              files={'file': (path.name, f, 'text/csv')},
                              timeout=180)
        return r.status_code, r.json()
    return post


def check(case, status, reply):
    exp, problems, got = case['expected'], [], {}
    want_status = exp.get('http_status', 200)
    got['http_status'] = status
    if status != want_status:
        return [f'HTTP {status}, expected {want_status}'], got
    if want_status != 200:
        if exp.get('error') and reply.get('error') != exp['error']:
            problems.append(f"error {reply.get('error')}, expected {exp['error']}")
        return problems, got
    d = reply.get('data', reply)
    zones = {z['parameter']: z for z in d.get('parameter_zones', [])}
    for p, want in exp.get('zones', {}).items():
        z = zones.get(p, {})
        got[p] = f"{z.get('value')} {z.get('zone')}"
        if z.get('zone') != want:
            true = case['true_values'].get(p)
            problems.append(f'{p}: {z.get("zone")} (measured {z.get("value")}, '
                            f'true {true}), expected {want}')
    signal = (d.get('traffic_light') or {}).get('signal')
    got['composite'] = signal
    if exp.get('composite') and signal != exp['composite']:
        problems.append(f"composite {signal}, expected {exp['composite']}")
    snr = d.get('audit_results', {}).get('snr', {})
    got['snr'] = f"{snr.get('linear')} {snr.get('status')}"
    if exp.get('snr_status') and snr.get('status') != exp['snr_status']:
        problems.append(f"SNR status {snr.get('status')} (SNR {snr.get('linear')}), "
                        f"expected {exp['snr_status']}")
    if exp.get('snr_band') and snr.get('linear') is not None:
        # The status must follow Table 2.3 for the SNR the API measured.
        # Whether the simulated SNR landed in the intended band is noted,
        # not failed: SNR estimates scatter at low SNR.
        book = book_snr_status(exp['snr_electrode'], float(snr['linear']))
        if snr.get('status') != book:
            problems.append(f"SNR {snr['linear']} gives {snr.get('status')}; "
                            f"Table 2.3 gives {book}")
        got['intended_band'] = exp['snr_band']
        got['band_hit'] = book == exp['snr_band']
        if book == 'FAIL' and signal in COLOURS:
            problems.append(f'Traffic Light {signal} given; a Fail recording '
                            'should get none (Chapter 2)')
    if exp.get('inverted_polarity_detected') and not d.get('features', {}).get(
            'inverted_polarity_detected'):
        problems.append('inverted polarity not detected')
    if exp.get('mains_detected'):
        mains = d.get('audit_results', {}).get('mains_interference', {})
        if not mains.get('detected_hz'):
            problems.append('50 Hz hum not detected')
    bundle = d.get('fhir_bundle') or {}
    if bundle.get('resourceType') != 'Bundle':
        problems.append('no FHIR Bundle returned')
    return problems, got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://localhost:8080')
    ap.add_argument('--local', action='store_true')
    args = ap.parse_args()
    manifest = json.loads((SET / 'manifest.json').read_text())
    post = poster(args.url, args.local)
    rows = []
    for case in manifest['cases']:
        try:
            status, reply = post(case['form'], SET / 'csv' / case['file'])
            problems, got = check(case, status, reply)
        except Exception as e:          # report, do not stop the run
            problems, got = [f'{type(e).__name__}: {e}'], {}
        rows.append({'id': case['id'], 'group': case['group'],
                     'result': 'PASS' if not problems else 'FAIL',
                     'problems': '; '.join(problems),
                     'got': json.dumps(got, ensure_ascii=False),
                     'proves': case['proves']})
        print(f"{rows[-1]['result']:4s} {case['id']}"
              + (f"  <- {rows[-1]['problems']}" if problems else ''))
    df = pd.DataFrame(rows)
    df.to_csv(SET / 'results.csv', index=False)
    print('\n' + df.groupby('group')['result'].value_counts().unstack(
        fill_value=0).to_string())
    n_pass = (df['result'] == 'PASS').sum()
    print(f'\nTotal: {n_pass}/{len(df)} PASS. Details: {SET / "results.csv"}')


if __name__ == '__main__':
    main()
