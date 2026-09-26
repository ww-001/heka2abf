"""Convert HEKA .dat bundles to ABF2 files.

Mapping (per the design decision):
  * one ABF2 file per HEKA series, written into <out_dir>/<dat-stem>/;
  * ABF channel    == HEKA ADC channel (traces sorted by ADC number);
  * ABF sweep      == HEKA sweep;
  * single-sweep series are written as gap-free ABFs, multi-sweep series as
    episodic ABFs (both follow real Clampfit file structures);
  * units normalize to mV (voltage) and pA (current) by default.
"""

import os

from .reader import load_dat
from .abf2writer import write_abf2


def _normalize_unit(unit):
    """Return (display_unit, scale) for HEKA trace units."""
    u = (unit or "").strip()
    if u == "V":
        return "mV", 1e3
    if u == "A":
        return "pA", 1e12
    if u == "":
        return "?", 1.0
    return u, 1.0


def _safe_write(write_abf2, out, *args, log, **kwargs):
    """Call write_abf2; on PermissionError warn and skip instead of raising."""
    try:
        write_abf2(out, *args, **kwargs)
        return out
    except PermissionError as e:
        log("!! 跳过（文件被占用，请先关闭 Clampfit 中的该文件）: %s" % out)
        log("   %s" % e)
        return None
    except OSError as e:
        log("!! 写入失败: %s (%s)" % (out, e))
        return None


def _matrix_for_sweep(sw, adc_channels, unit_scales):
    """Return (samples, nCh) float32 matrix with per-channel traces aligned
    and scaled to normalized units."""
    import numpy as np
    lengths = {ch.adc_channel: len(ch) for ch in sw.channels}
    if len(set(lengths.values())) != 1:
        raise ValueError(
            "sweep %d has traces of different lengths: %s"
            % (sw.sweep_idx, lengths))
    n_points = sw.channels[0].samples.shape[0]
    mat = np.zeros((n_points, len(adc_channels)), dtype=np.float32)
    for col, adc in enumerate(adc_channels):
        ch = sw.channel_by_adc(adc)
        if ch is not None:
            mat[:, col] = ch.samples * unit_scales[col]
    return mat


def _pad_to_fixed(sweeps):
    """Pad shorter sweeps to the longest length (hold last value).

    Clampfit displays episodic files most reliably when all sweeps have the
    same length; HEKA commonly contains series where the final sweep was cut
    short (interrupted recording).  Padding the tail keeps the file
    fixed-length while preserving all recorded data.
    """
    import numpy as np
    maxlen = max(m.shape[0] for m in sweeps)
    n_ch = sweeps[0].shape[1]
    if all(m.shape[0] == maxlen for m in sweeps):
        return sweeps
    out = []
    for m in sweeps:
        n = m.shape[0]
        if n == maxlen:
            out.append(m)
            continue
        padded = np.empty((maxlen, n_ch), dtype=np.float32)
        padded[:n] = m
        padded[n:] = m[-1]            # hold the last recorded value
        out.append(padded)
    return out


def _filename_base(stem, series, channel=None):
    label = "".join(c for c in series.label if c.isalnum() or c in "._-")
    label = label or "series"
    base = "%s_g%d_s%d_%s" % (stem, series.group_idx + 1, series.series_idx + 1, label)
    if channel is not None:
        base += "_adc%d" % channel
    return base


def convert_dat(dat_path, out_dir=".", one_file_per_channel=False,
                mode="auto", log=print):
    """Convert a HEKA .dat bundle; writes one or more .abf files.

    Output files land in <out_dir>/<dat file stem>/ .

    mode : "auto" | "episodic" | "gapfree"
        auto: single-sweep series become gap-free, multi-sweep episodic.
    log : callable(str)
        Receives warning messages (e.g. skip of a file locked by Clampfit).

    Returns list of output paths written.  Series whose output file is locked
    (PermissionError, e.g. open in Clampfit) are skipped with a warning
    instead of aborting the whole conversion.
    """
    series_list = load_dat(dat_path)
    if not series_list:
        raise ValueError("no series found in %s" % dat_path)

    stem = os.path.splitext(os.path.basename(dat_path))[0]
    dest = os.path.join(out_dir, stem)
    os.makedirs(dest, exist_ok=True)
    written = []

    for series in series_list:
        if not series.sweeps:
            continue
        interval_us = series.sampling_interval_s() * 1e6

        if one_file_per_channel:
            for adc in series.all_adc_channels():
                ch0 = None
                sweeps = []
                times = []
                for sw in series.sweeps:
                    ch = sw.channel_by_adc(adc)
                    if ch is None:
                        continue
                    import numpy as np
                    unit, scale = _normalize_unit(ch.unit if ch.unit else "")
                    mat = (ch.samples * scale).reshape(-1, 1)
                    sweeps.append(mat)
                    times.append(sw.time_s)
                    if ch0 is None:
                        ch0 = ch
                if not sweeps:
                    continue
                sweeps = _pad_to_fixed(sweeps)
                out = os.path.join(dest,
                                   _filename_base(stem, series, channel=adc) + ".abf")
                ok = _safe_write(
                    write_abf2, out, sweeps,
                    channel_names=[ch0.label], channel_units=[unit],
                    sample_interval_us=interval_us,
                    protocol_path=os.path.basename(dat_path),
                    sweep_times_s=times, mode=mode, log=log)
                if ok:
                    written.append(ok)
        else:
            adc_channels = series.all_adc_channels()
            # representative labels/units/scales per channel (first sweep)
            names, units, scales = [], [], []
            for adc in adc_channels:
                ch = None
                for sw in series.sweeps:
                    ch = sw.channel_by_adc(adc)
                    if ch is not None:
                        break
                unit, scale = _normalize_unit(ch.unit if ch else "")
                names.append(ch.label if ch else ("Ch%d" % adc))
                units.append(unit)
                scales.append(scale)
            sweeps = _pad_to_fixed([_matrix_for_sweep(sw, adc_channels, scales)
                                    for sw in series.sweeps])
            times = [sw.time_s for sw in series.sweeps]
            out = os.path.join(dest, _filename_base(stem, series) + ".abf")
            ok = _safe_write(
                write_abf2, out, sweeps,
                channel_names=names, channel_units=units,
                sample_interval_us=interval_us,
                protocol_path=os.path.basename(dat_path),
                sweep_times_s=times, mode=mode, log=log)
            if ok:
                written.append(ok)

    return written