"""Reading HEKA PatchMaster .dat files (via the heka_reader package).

heka_reader (https://github.com/campagnola/heka_reader) is vendored into the
venv as a plain module; this wrapper exposes the parts the converter needs:
  * enumerate groups / series / sweeps / traces,
  * per-trace physical-unit samples (already scaled by DataScaler/ZeroData),
  * sample interval (XInterval, seconds) and unit (YUnit).

Known limitation: heka_reader reads the stored sample array verbatim, so
traces written with PatchMaster's optional lossy compression would come back
as raw min/max pairs.  Standard patch-clamp recordings are uncompressed.
"""

import numpy as np


class HekaChannel:
    """One recording channel inside a HEKA sweep (one trace)."""

    def __init__(self, adc_channel, label, unit, samples, x_interval_s):
        self.adc_channel = int(adc_channel)   # HEKA ADC channel number
        self.label = label or ("Ch%d" % adc_channel)
        self.unit = unit or "?"
        self.samples = np.asarray(samples, dtype=np.float32)
        self.x_interval_s = float(x_interval_s)

    def __len__(self):
        return len(self.samples)


class HekaSweep:
    """All traces recorded in one HEKA sweep."""

    def __init__(self, group_idx, series_idx, sweep_idx, channels, time_s=0.0):
        self.group_idx = group_idx
        self.series_idx = series_idx
        self.sweep_idx = sweep_idx
        self.channels = channels          # list[HekaChannel]
        self.time_s = float(time_s)       # sweep start time (seconds)

    def channel_by_adc(self, adc):
        for ch in self.channels:
            if ch.adc_channel == adc:
                return ch
        return None


class HekaSeries:
    """One HEKA series: label + list of sweeps."""

    def __init__(self, group_idx, series_idx, label, sweeps):
        self.group_idx = group_idx
        self.series_idx = series_idx
        self.label = label
        self.sweeps = sweeps

    def all_adc_channels(self):
        seen = []
        for sw in self.sweeps:
            for ch in sw.channels:
                if ch.adc_channel not in seen:
                    seen.append(ch.adc_channel)
        return sorted(seen)

    def sampling_interval_s(self):
        """Common XInterval across traces; raises if inconsistent."""
        vals = {}
        for sw in self.sweeps:
            for ch in sw.channels:
                vals[round(ch.x_interval_s, 12)] = ch.x_interval_s
        if len(vals) > 1:
            raise ValueError(
                "series %r mixes sampling intervals %s; convert series separately"
                % (self.label, sorted(vals)))
        if not vals:
            raise ValueError("series %r contains no traces" % self.label)
        return vals[list(vals.keys())[0]]


def load_dat(path):
    """Return list[HekaSeries] describing the whole .dat bundle."""
    import heka_reader
    bundle = heka_reader.Bundle(path)
    pul = bundle.pul
    data = bundle.data
    series_list = []
    for g in range(len(pul)):
        group = pul[g]
        for s in range(len(group)):
            series = group[s]
            label = series.Label or ""
            sweeps = []
            for sw in range(len(series)):
                sweep = series[sw]
                channels = []
                for t in range(len(sweep)):
                    trace = sweep[t]
                    samples = data[g, s, sw, t]
                    channels.append(HekaChannel(
                        adc_channel=getattr(trace, "AdcChannel", len(channels)),
                        label=trace.Label,
                        unit=trace.YUnit,
                        samples=samples,
                        x_interval_s=trace.XInterval,
                    ))
                sweeps.append(HekaSweep(g, s, sw, channels,
                                        time_s=getattr(sweep, "Time", 0.0)))
            series_list.append(HekaSeries(g, s, label, sweeps))
    return series_list


def control_date_summary(series_list):
    """Small human-readable summary (groups x series x sweeps x channels)."""
    lines = []
    for ser in series_list:
        n_sw = len(ser.sweeps)
        n_ch = None
        if ser.sweeps:
            n_ch = len(ser.sweeps[0].channels)
        lines.append("  group %d series %d '%s': %d sweep(s), %d trace(s)/sweep, %.4g s/point"
                     % (ser.group_idx + 1, ser.series_idx + 1, ser.label,
                        n_sw, n_ch or 0,
                        ser.sampling_interval_s() if ser.sweeps else 0))
    return "\n".join(lines)