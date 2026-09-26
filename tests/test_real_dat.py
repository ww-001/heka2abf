"""End-to-end validation on REAL HEKA .dat files:

    heka .dat --(heka_reader)--> physical samples
                                   |
                                   v
                              write_abf2 -> .abf
                                   |
                                   v
                            pyabf readback
                                   |
                                   v
              compare every sample (all sweeps x channels) numerically

Run:  python tests/test_real_dat.py [dat1 dat2 ...]
(defaults to the files in D:\\heka test\\test file)

This test is marked ``real_dat`` and is SKIPPED by default on CI because it
requires real HEKA .dat files at hard-coded paths.  To run it locally:

    pytest tests/test_real_dat.py -v -m real_dat            # only this test
    pytest tests/test_real_dat.py -v -m real_dat -- <files>  # pass files via argv

Or via the legacy script entry-point (still works):

    python tests/test_real_dat.py path/to/file1.dat path/to/file2.dat ...
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heka2abf.abf2writer import write_abf2  # noqa: E402
from heka2abf.reader import load_dat  # noqa: E402

# This entire module is gated by the ``real_dat`` pytest marker so it is
# excluded from ``pytest tests/`` on CI (see pyproject.toml [tool.pytest.ini_options]
# addopts + the default-marker-skip convention below).  Run it locally with
# ``pytest -m real_dat`` to exercise the end-to-end path.
pytestmark = pytest.mark.real_dat


def _candidate_default_dats():
    folder = r"D:\heka test\test file"
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(".dat")]


def _dats_to_run(argv):
    if argv:
        # When pytest is driving us, sys.argv[1:] is the user-supplied CLI args
        # (e.g. ``--``-separated test names); for the legacy script entry we
        # accept file paths.
        return [a for a in argv if a.lower().endswith(".dat")]
    return _candidate_default_dats()


def validate_one(dat_path, out_dir, max_series=3):
    series_list = load_dat(dat_path)
    checked = 0
    rows = []
    for ser in series_list:
        if checked >= max_series:
            break
        if not ser.sweeps:
            continue
        interval_us = ser.sampling_interval_s() * 1e6
        adc_channels = ser.all_adc_channels()
        # expected per-sweep matrix from heka (sweeps may vary in length)
        mats = []
        for sw in ser.sweeps:
            n = len(sw.channels[0].samples)
            m = np.zeros((n, len(adc_channels)), dtype=np.float32)
            for col, adc in enumerate(adc_channels):
                ch = sw.channel_by_adc(adc)
                if ch is not None:
                    m[:, col] = ch.samples
            mats.append(m)
        names = []
        units = []
        for adc in adc_channels:
            ch = None
            for sw in ser.sweeps:
                ch = sw.channel_by_adc(adc)
                if ch is not None:
                    break
            names.append(ch.label if ch else "Ch%d" % adc)
            units.append(ch.unit if ch else "?")
        out = os.path.join(out_dir, "v_%d.abf" % checked)
        write_abf2(out, mats, channel_names=names, channel_units=units,
                   sample_interval_us=interval_us,
                   protocol_path=os.path.basename(dat_path),
                   sweep_times_s=[sw.time_s for sw in ser.sweeps])
        # read back
        import pyabf
        abf = pyabf.ABF(out)
        assert abf.channelCount == len(adc_channels)
        assert abf.sweepCount == len(mats)
        assert abs(abf.dataRate - 1e6 / interval_us) < 1
        assert abf.adcNames == names, (abf.adcNames, names)
        assert abf.adcUnits == units, (abf.adcUnits, units)
        lengths = {len(m) for m in mats}
        if len(lengths) == 1:
            assert abf.sweepPointCount == mats[0].shape[0]
        worst = 0.0
        worst_tol = 0.0
        for s in range(len(mats)):
            for c in range(len(adc_channels)):
                abf.setSweep(s, channel=c)
                if len(abf.sweepY) != len(mats[s]):
                    raise AssertionError(
                        "sweep %d length %d != %d" %
                        (s, len(abf.sweepY), len(mats[s])))
                peak = float(np.max(np.abs(mats[s][:, c]))) or 1e-9
                tol = max(1e-6, peak * 1e-4)   # int16 quantization bound
                d = float(np.max(np.abs(abf.sweepY - mats[s][:, c])))
                worst = max(worst, d)
                worst_tol = max(worst_tol, tol)
        if worst > worst_tol:
            raise AssertionError("series %r max diff %.3g exceeds tol %.3g"
                                 % (ser.label, worst, worst_tol))
        checked += 1
        yield ser.label, len(adc_channels), len(mats), worst


def main(argv):
    dats = _dats_to_run(argv)
    if not dats:
        print("No .dat files to validate (set D:\\heka test\\test file or pass "
              "paths on the command line).  Exiting 0 (nothing to fail).")
        return 0
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vout")
    os.makedirs(out_dir, exist_ok=True)
    total_bad = 0
    for dat in dats:
        print("=== %s ===" % os.path.basename(dat))
        try:
            for label, n_ch, n_sw, worst in validate_one(dat, out_dir):
                print("  series '%s': %d ch x %d sweeps, max abs diff = %.3g"
                      % (label, n_ch, n_sw, worst))
                if worst > 1e-3:
                    total_bad += 1
        except Exception as e:
            import traceback
            traceback.print_exc()
            total_bad += 1
    print("\nRESULT:", "FAIL" if total_bad else "ALL REAL-FILE ROUNDTRIPS PASSED")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))