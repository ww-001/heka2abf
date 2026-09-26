"""Validate the ABF2 writer by reading its output back with pyABF.

Run:  python tests/test_abf2writer.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from heka2abf.abf2writer import write_abf2  # noqa: E402


def _read_back(path):
    import pyabf
    return pyabf.ABF(path)  # loadData=True


def _tol(channel):
    """int16 quantization bound: LSB = peak/30000, allow 3x plus epsilon."""
    return max(1e-6, float(np.max(np.abs(channel))) * 1e-4)


def test_synthetic_roundtrip():
    rng = np.random.default_rng(42)
    n_ch = 2
    n_pts = 100
    n_sw = 3
    interval_us = 50.0  # 20 kHz
    sweeps = []
    for s in range(n_sw):
        mat = rng.normal(size=(n_pts, n_ch)).astype(np.float32)
        mat[:, 0] += s  # offset between sweeps
        sweeps.append(mat)

    out = os.path.join(os.path.dirname(__file__), "synthetic.abf")
    write_abf2(out, sweeps,
               channel_names=["Vmon", "Imon"], channel_units=["mV", "pA"],
               sample_interval_us=interval_us)

    abf = _read_back(out)
    assert abf.abfVersion["major"] == 2, "not an ABF2 file"
    assert abf._nDataFormat == 0, "expected int16 storage"
    assert abf.nOperationMode == 5, "multi-sweep file should be episodic"
    assert abf.channelCount == n_ch, abf.channelCount
    assert abf.sweepCount == n_sw, abf.sweepCount
    assert abf.sweepPointCount == n_pts, abf.sweepPointCount
    assert abs(abf.dataRate - 1e6 / interval_us) < 1, abf.dataRate
    assert abf.adcUnits == ["mV", "pA"], abf.adcUnits
    assert abf.adcNames == ["Vmon", "Imon"], abf.adcNames

    for s in range(n_sw):
        for c in range(n_ch):
            abf.setSweep(s, channel=c)
            got = abf.sweepY
            expect = sweeps[s][:, c]
            assert np.max(np.abs(got - expect)) <= _tol(expect), \
                "sweep %d channel %d mismatch" % (s, c)
    print("test_synthetic_roundtrip OK (int16 episodic)")


def test_single_sweep_gapfree():
    rng = np.random.default_rng(7)
    sw = (rng.normal(size=(5000, 1)) * 0.07).astype(np.float32)  # ~mV
    out = os.path.join(os.path.dirname(__file__), "gapfree.abf")
    write_abf2(out, [sw], channel_names=["Vmon"], channel_units=["mV"],
               sample_interval_us=100.0)
    abf = _read_back(out)
    assert abf.nOperationMode == 3, "single sweep should become gap-free"
    assert abf.sweepCount == 1 and abf.channelCount == 1
    assert abf._synchArraySection._entryCount == 0, "gap-free has no SIC"
    abf.setSweep(0)
    assert np.max(np.abs(abf.sweepY - sw[:, 0])) <= _tol(sw[:, 0])
    print("test_single_sweep_gapfree OK")


def test_reference_emulation():
    """Read a real Clampfit ABF2 (int16, 50 sweeps) and re-write it with our
    writer; verify pyABF reads back the same physical values (within int16
    quantization)."""
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(here, "..", "reference", "model_vc_ramp.abf")
    if not os.path.exists(ref):
        print("reference file missing; skipping test_reference_emulation")
        return

    import pyabf
    src = pyabf.ABF(ref)
    sweeps = []
    for s in range(src.sweepCount):
        src.setSweep(s)
        sweeps.append(src.sweepY.reshape(-1, 1))

    out = os.path.join(here, "emulated.abf")
    write_abf2(out, sweeps,
               channel_names=["IN 0"], channel_units=["pA"],
               sample_interval_us=1e6 / src.dataRate)

    dst = pyabf.ABF(out)
    assert dst.abfVersion["major"] == 2
    assert dst._nDataFormat == 0
    assert dst.channelCount == 1 and dst.sweepCount == src.sweepCount
    assert dst.sweepPointCount == src.sweepPointCount
    assert abs(dst.dataRate - src.dataRate) < 1

    maxdiff = 0.0
    for s in range(src.sweepCount):
        src.setSweep(s); dst.setSweep(s)
        d = float(np.max(np.abs(src.sweepY - dst.sweepY)))
        maxdiff = max(maxdiff, d)
    tol = _tol(sweeps[0][:, 0])
    print("test_reference_emulation OK  (max abs diff %.3g, tol %.3g)"
          % (maxdiff, tol))
    assert maxdiff <= tol


if __name__ == "__main__":
    test_synthetic_roundtrip()
    test_single_sweep_gapfree()
    test_reference_emulation()
    print("ALL TESTS PASSED")