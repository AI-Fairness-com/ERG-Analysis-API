"""Shared helpers for the nine case notebooks of Chapter 19.

Each notebook lists a case's values from its Chapter 19 table and
uses the pipeline in api/erg_v2_5_0.py to assign the Traffic Light
zones (Chapter 10 Section 10.4, Equation 10.2), then checks them
against the zones printed in the book. The case values are
constructed for teaching; they are not patient data.
"""
import contextlib
import io
import os
import sys
from pathlib import Path

import pandas as pd

# Repository root: the folder that holds api/ (works from examples/,
# from the root, or in Colab after cloning)
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents,
                        Path('/content/ERG-Analysis-API')]
            if (p / 'api' / 'erg_v2_5_0.py').exists())
sys.path.insert(0, str(ROOT / 'api'))
os.chdir(ROOT)

# Import the pipeline quietly: hide its cell banners and the Colab
# upload form of Cell 10, which these notebooks do not use
import IPython.display as _ipd
_show = _ipd.display
_ipd.display = lambda *args, **kwargs: None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        import erg_v2_5_0 as erg
finally:
    _ipd.display = _show

REPORT = erg.ERGReportGenerator()

# Book parameter names -> pipeline feature keys
FEATURE = {'a-wave amplitude': 'a_amp_uv',
           'a-wave implicit time': 'a_implicit_ms',
           'b-wave amplitude': 'b_amp_uv',
           'b-wave implicit time': 'b_implicit_ms',
           'flicker amplitude': 'b_amp_uv',
           'flicker implicit time': 'b_implicit_ms'}


def zone_table(rows, age, electrode='dtl_fiber'):
    """
    rows: (protocol, parameter, value, zone printed in the book), and
    optionally the (lower, upper) limits printed in the book, which
    are then checked against the normative file too. Parameters without published limits (PhNR, OPs, b/a ratio) are
    listed as 'NOT ZONED'. Returns the table and the composite
    Traffic Light (the most severe zone).
    """
    out, zoned = [], []
    for protocol, parameter, value, book, *printed in rows:
        if parameter not in FEATURE:
            out.append([protocol, parameter, value, '', 'NOT ZONED',
                        book, book.upper() in ('NOT ZONED', '')])
            continue
        res = REPORT.classify_parameters({FEATURE[parameter]: value},
                                         electrode, protocol, age)
        r = next(x for x in res if x['feature'] == FEATURE[parameter])
        zoned.append(r)
        limits = (f"{r['lower_limit']:g} to {r['upper_limit']:g} "
                  f"(L_lo {r['lower_ci_low']:g}, U_hi "
                  f"{r['upper_ci_high']:g})")
        match = r['zone'] == book.upper()
        if printed:
            match = match and tuple(printed[0]) == (r['lower_limit'],
                                                    r['upper_limit'])
        out.append([protocol, parameter, value, limits, r['zone'], book,
                    match])
    table = pd.DataFrame(out, columns=[
        'Protocol', 'Parameter', 'Value', 'Limits', 'Zone (code)',
        'Zone (book)', 'Match'])
    signal = REPORT.composite_traffic_light(
        zoned, REPORT._normalise_electrode(electrode))['signal']
    return table, signal


def check(table):
    """Print whether every zone matches the book."""
    wrong = table[~table['Match']]
    if wrong.empty:
        print(f'All {len(table)} rows match the zones printed in '
              'Chapter 19.')
    else:
        print('Rows that differ from the book:')
        print(wrong.to_string(index=False))
