"""Self-contained ABF2 (Axon Binary Format version 2) writer.

The layout implemented here mirrors REAL Clampfit/pClamp ABF2 files
(reverse-engineered with tools/abf2_dump.py from files in reference/ and
cross-checked against the pyABF reader, which reads everything this module
writes).

Facts learned from real files that matter for Clampfit compatibility:
  * data format is int16 (uComprType/nDataFormat = 0) with the signal
    reconstructed by the reader from the header gain chain
    (fADCRange/lADCResolution / InstrumentScaleFactor / SignalGain /
    ProgrammableGain);
  * the header's first 4 KB contain the FB file section at bytes 0..75 and
    fixed-position 16-byte section descriptors from byte 76:
        PIL @ 76, ADC @ 92, DAC @ 108, STR @ 220, DATA @ 236, SIC @ 316;
  * the "size" field of a descriptor is the PER-ENTRY byte size (ADC = 128);
  * lNumSamplesPerEpisode counts MULTIPLEXED samples (channels x points);
  * episodic files (mode 5) use a SIC synch array; gap-free files (mode 3)
    do not (SIC absent);
  * nSimultaneousScan is 1 for episodic files and 0 for gap-free files;
  * there are no EPC/EPE/TAG sections in these simple files;
  * the STR section is a single entry: 'SSCH' + version + count + two offset
    fields + 24 zero bytes + N null-terminated strings.

Data is stored as int16 with per-channel scale factors chosen so the raw
values use the 16-bit range; unit strings are set on the ADC entries.
"""

import os
import struct
import time

BLOCKSIZE = 512
SECTION_POS = {
    "PIL": 76,
    "ADC": 92,
    "DAC": 108,
    "EPE": 124,
    "EPC": 140,
    "TAG": 156,
    "STR": 220,
    "DATA": 236,
    "SIC": 316,
}
ADC_ENTRY_BYTES = 128

OP_MODE_EPISODIC = 5
OP_MODE_GAPFREE = 3


def _now_fields():
    """Return (uFileStartDate YYYYMMDD, uFileStartTimeMS) for the current time."""
    t = time.localtime()
    date = t.tm_year * 10000 + t.tm_mon * 100 + t.tm_mday
    ms = int(((t.tm_hour * 60 + t.tm_min) * 60 + t.tm_sec) * 1000)
    return date, ms


def _build_strings_section(creator, protocol_path, channel_names, channel_units):
    """Build the STR section blob following the Clampfit 'SSCH' layout.

    Indexing convention (verified against pyABF's parser, which starts the
    indexed-string list at the last '\\x00\\x00' in the entry):
        indexed[0] = '' (empty, parse artifact)
        indexed[1] = creator
        indexed[2] = protocol path
        indexed[3..] = per-channel name / unit pairs
    """
    if not protocol_path:
        protocol_path = "None"          # avoid empty-string double-NUL
    strings = [creator, protocol_path]
    for name, unit in zip(channel_names, channel_units):
        strings.append(name if name else "Unknown")
        strings.append(unit if unit else "?")
    payload = b"".join(s.encode("ascii", "ignore") + b"\x00" for s in strings)
    entry = bytearray()
    entry += b"SSCH"
    entry += struct.pack("<I", 1)                       # format version
    entry += struct.pack("<I", len(strings))            # string count
    entry += struct.pack("<I", 44 + len(strings[0]) + 1)
    entry += struct.pack("<I", 44 + len(payload))
    entry += b"\x00" * 24
    entry += payload
    return bytes(entry)


def _write_fb(header, *, episodes, channels, data_format=0, n_simultaneous=1):
    """Write the 75-byte FB file section fields."""
    date, ms = _now_fields()
    header[0:4] = b"ABF2"
    header[4:8] = struct.pack("<4B", 6, 0, 0, 2)        # file version 2.0.0.6
    struct.pack_into("<I", header, 8, 512)              # uFileInfoSize
    struct.pack_into("<I", header, 12, episodes)        # lActualEpisodes
    struct.pack_into("<I", header, 16, date)            # uFileStartDate
    struct.pack_into("<I", header, 20, ms)              # uFileStartTimeMS
    struct.pack_into("<I", header, 24, 0)               # uStopwatchTime
    struct.pack_into("<H", header, 28, 1)               # nFileType
    struct.pack_into("<H", header, 30, data_format)     # nDataFormat (0 int16, 1 float32)
    struct.pack_into("<H", header, 32, n_simultaneous)  # nSimultaneousScan
    struct.pack_into("<H", header, 34, 0)               # nCRCEnable
    struct.pack_into("<I", header, 36, 0)               # uFileCRC
    header[40:56] = os.urandom(16)                      # uFileGUID
    header[56:60] = struct.pack("<4B", 2, 0, 0, 6)      # uCreatorVersion
    struct.pack_into("<I", header, 60, 1)               # uCreatorNameIndex
    struct.pack_into("<I", header, 64, 0)               # uModifierVersion
    struct.pack_into("<I", header, 68, 0)               # uModifierNameIndex
    struct.pack_into("<I", header, 72, 2)               # uProtocolPathIndex


def _build_pil(sample_interval_us, *, mode, episodes, samples_per_episode,
               n_channels, max_points_per_channel):
    """Protocol section (512 bytes, 1 item). Offsets per pyABF protocolSection."""
    pil = bytearray(512)
    struct.pack_into("<h", pil, 0, mode)                       # nOperationMode
    struct.pack_into("<f", pil, 2, float(sample_interval_us))  # fADCSequenceInterval
    pil[6] = 0                                                 # bEnableFileCompression
    struct.pack_into("<i", pil, 10, 1)                         # uFileCompressionRatio
    struct.pack_into("<f", pil, 14, 1e6)                       # fSynchTimeUnit (usec)
    if mode == OP_MODE_EPISODIC:
        struct.pack_into("<f", pil, 18, 0.0)                   # fSecondsPerRun
        struct.pack_into("<i", pil, 22, samples_per_episode)   # MULTIPLEXED samples/episode
        struct.pack_into("<i", pil, 26, 0)                     # lPreTriggerSamples
        struct.pack_into("<i", pil, 30, episodes)              # lEpisodesPerRun
        struct.pack_into("<i", pil, 34, 1)                     # lRunsPerTrial
        struct.pack_into("<i", pil, 38, 1)                     # lNumberOfTrials
        struct.pack_into("<h", pil, 42, 0)                     # nAveragingMode
        struct.pack_into("<h", pil, 44, 0)                     # nUndoRunCount
        struct.pack_into("<h", pil, 46, 0)                     # nFirstEpisodeInRun
        struct.pack_into("<f", pil, 62, 0.0)                   # fEpisodeStartToStart
        struct.pack_into("<i", pil, 86, 0)                     # lSamplesPerTrace
        struct.pack_into("<i", pil, 94, max_points_per_channel)  # lFinishDisplayNum
    else:  # gap-free: mirror real pClamp gap-free files
        # 4000 samples/chunk and 20000 samples/trace are the values real
        # Clampfit gap-free files carry; Clampfit segments the display on
        # these numbers, so arbitrary values break the display.
        struct.pack_into("<f", pil, 14, 0.0)                     # fSynchTimeUnit
        struct.pack_into("<i", pil, 22, 4000)                    # samples per chunk
        struct.pack_into("<i", pil, 26, 40)                      # lPreTriggerSamples (real: 40)
        struct.pack_into("<i", pil, 30, 1)                       # lEpisodesPerRun
        struct.pack_into("<i", pil, 86, 20000)                   # lSamplesPerTrace (real: 20000)
        struct.pack_into("<i", pil, 94, 0)                       # lFinishDisplayNum
        struct.pack_into("<h", pil, 138, 1)                      # nSignalType (real: 1)
    struct.pack_into("<f", pil, 110, 10.0)                   # fADCRange
    struct.pack_into("<f", pil, 114, 10.0)                   # fDACRange
    struct.pack_into("<i", pil, 118, 32768)                  # lADCResolution
    struct.pack_into("<i", pil, 122, 32768)                  # lDACResolution
    struct.pack_into("<h", pil, 126, 2)                      # nExperimentType
    struct.pack_into("<h", pil, 198, n_channels)             # nDigitizerADCs
    struct.pack_into("<h", pil, 200, 0)                      # nDigitizerDACs
    struct.pack_into("<h", pil, 206, 6)                      # nDigitizerType
    return bytes(pil)


def _build_adc(n_channels, name_indices, unit_indices, scale_factors):
    """ADC section, one 128-byte (padded) entry per channel."""
    out = bytearray(n_channels * ADC_ENTRY_BYTES)
    for i in range(n_channels):
        b = i * ADC_ENTRY_BYTES
        struct.pack_into("<h", out, b + 0, i)                 # nADCNum
        struct.pack_into("<h", out, b + 24, i)                # nADCPtoLChannelMap
        struct.pack_into("<h", out, b + 26, i)                # nADCSamplingSeq
        struct.pack_into("<f", out, b + 28, 1.0)              # fADCProgrammableGain
        struct.pack_into("<f", out, b + 32, 1.0)              # fADCDisplayAmplification
        struct.pack_into("<f", out, b + 36, 0.0)              # fADCDisplayOffset
        struct.pack_into("<f", out, b + 40, scale_factors[i])  # fInstrumentScaleFactor
        struct.pack_into("<f", out, b + 44, 0.0)              # fInstrumentOffset
        struct.pack_into("<f", out, b + 48, 1.0)              # fSignalGain
        struct.pack_into("<f", out, b + 52, 0.0)              # fSignalOffset
        struct.pack_into("<i", out, b + 74, name_indices[i])  # lADCChannelNameIndex
        struct.pack_into("<i", out, b + 78, unit_indices[i])  # lADCUnitsIndex
    return bytes(out)


def _build_sic(episodes, start_units, lengths):
    """Synch array: one (lStart, lLength) pair per episode."""
    out = bytearray()
    for i in range(episodes):
        out += struct.pack("<ii", int(start_units[i]), int(lengths[i]))
    return bytes(out)


def _quantize_int16(sweeps):
    """Convert physical-unit sweeps to int16 + per-channel scale factors.

    Physical value = raw * (fADCRange/lADCResolution) / (F * 1 * 1), so we
    choose F[i] so each channel's peak sits around 30000 raw counts.
    Returns (raw int16 array interleaved, per-channel F list, lsb list).
    """
    import numpy as np
    n_channels = sweeps[0].shape[1]
    lsb = []
    scales = []
    quantized = []
    for c in range(n_channels):
        peak = max(float(np.max(np.abs(sw[:, c]))) for sw in sweeps)
        if peak <= 0 or not np.isfinite(peak):
            peak = 1e-9
        # raw = value * 3276.8 * F ;  choose F so peak -> ~30000 counts
        f = (30000.0 / peak) / 3276.8
        lsb_c = (10.0 / 32768.0) / f          # physical units per raw count
        scales.append(f)
        lsb.append(lsb_c)
        for sw in sweeps:
            raw = np.clip(np.rint(sw[:, c] / lsb_c), -32768, 32767)
            quantized.append(raw.astype(np.int16))
    # interleave: for each sweep, stack channels and flatten
    n_sw = len(sweeps)
    blocks = []
    for s in range(n_sw):
        cols = [quantized[c * n_sw + s] for c in range(n_channels)]
        blocks.append(np.stack(cols, axis=-1).reshape(-1))
    raw = np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.int16)
    return raw, scales, lsb


def write_abf2(path, sweeps, *, channel_names, channel_units,
               sample_interval_us, creator="heka2abf", protocol_path="",
               sweep_times_s=None, data_format="int16", mode="auto"):
    """Write an ABF2 file.

    Parameters
    ----------
    path : str
        Output file path.
    sweeps : list[np.ndarray]
        Each element is a 2D float array of shape (samples, nChannels) holding
        PHYSICAL-unit data, one per sweep.  Sweeps may have different lengths
        (described by the SIC section in episodic mode).
    channel_names, channel_units : list[str]
        Per-channel label / unit (len == nChannels).
    sample_interval_us : float
        Per-channel sampling interval in microseconds.
    sweep_times_s : list[float] | None
        Per-sweep start times (seconds); SIC start values are derived from
        them relative to the first sweep.  Ignored in gap-free mode.
    data_format : "int16" | "float32"
        Storage format.  int16 is what real Clampfit files use.
    mode : "auto" | "episodic" | "gapfree"
        auto: gap-free if there is a single sweep, else episodic.
    """
    import numpy as np

    sweeps = [np.asarray(s, dtype=np.float32) for s in sweeps]
    n_channels = sweeps[0].shape[1]
    n_episodes = len(sweeps)
    per_sweep_points = [s.shape[0] for s in sweeps]
    max_points = max(per_sweep_points)

    if mode == "auto":
        mode = OP_MODE_GAPFREE if n_episodes == 1 else OP_MODE_EPISODIC
    elif mode == "episodic":
        mode = OP_MODE_EPISODIC
    elif mode == "gapfree":
        mode = OP_MODE_GAPFREE
    else:
        raise ValueError("invalid mode %r" % mode)

    int16 = data_format == "int16"
    if data_format not in ("int16", "float32"):
        raise ValueError("data_format must be 'int16' or 'float32'")

    # ---- quantize ----
    if int16:
        raw, scales, lsb = _quantize_int16(sweeps)
        entry_bytes = 2
        n_raw = len(raw)
    else:
        raw = None
        scales = [1.0] * n_channels
        blocks = []
        for sw in sweeps:
            inter = np.stack([sw[:, c] for c in range(n_channels)], axis=-1)
            blocks.append(inter.reshape(-1))
        flat = np.concatenate(blocks) if blocks else np.zeros(0, np.float32)
        entry_bytes = 4
        n_raw = len(flat)

    # ---- strings ----
    str_blob = _build_strings_section(creator, protocol_path, channel_names, channel_units)
    name_indices = [3 + 2 * i for i in range(n_channels)]
    unit_indices = [4 + 2 * i for i in range(n_channels)]

    pil = _build_pil(
        sample_interval_us, mode=mode, episodes=n_episodes,
        samples_per_episode=max_points * n_channels,   # MULTIPLEXED, as real files
        n_channels=n_channels, max_points_per_channel=max_points)
    adc = _build_adc(n_channels, name_indices, unit_indices, scales)

    if mode == OP_MODE_EPISODIC:
        # SIC: start times in fSynchTimeUnit units (usec), lengths multiplexed
        if sweep_times_s is None:
            starts_us = [i * max_points * sample_interval_us
                         for i in range(n_episodes)]
        else:
            t0 = sweep_times_s[0]
            starts_us = [int(round((t - t0) * 1e6)) for t in sweep_times_s]
        lengths = [pts * n_channels for pts in per_sweep_points]
        sic = _build_sic(n_episodes, starts_us, lengths)
    else:
        sic = b""

    # ---- layout: every section on a 512-byte boundary ----
    def next_block_size(nbytes):
        return (nbytes + BLOCKSIZE - 1) // BLOCKSIZE * BLOCKSIZE

    data_bytes = n_raw * entry_bytes
    offset_str = 8 * BLOCKSIZE
    offset_pil = offset_str + next_block_size(len(str_blob))
    offset_adc = offset_pil + next_block_size(len(pil))
    offset_data = offset_adc + next_block_size(len(adc))
    offset_sic = offset_data + next_block_size(data_bytes)

    header = bytearray(4096)
    # gap-free files carry lActualEpisodes = 0 (as real Clampfit files do)
    _write_fb(header, episodes=0 if mode == OP_MODE_GAPFREE else n_episodes,
              channels=n_channels,
              data_format=0 if int16 else 1,
              n_simultaneous=0 if mode == OP_MODE_GAPFREE else 1)
    struct.pack_into("<III", header, SECTION_POS["PIL"],
                     offset_pil // BLOCKSIZE, 512, 1)
    struct.pack_into("<III", header, SECTION_POS["ADC"],
                     offset_adc // BLOCKSIZE, ADC_ENTRY_BYTES, n_channels)
    struct.pack_into("<III", header, SECTION_POS["STR"],
                     offset_str // BLOCKSIZE, len(str_blob), 1)
    struct.pack_into("<III", header, SECTION_POS["DATA"],
                     offset_data // BLOCKSIZE, entry_bytes, n_raw)
    if sic:
        struct.pack_into("<III", header, SECTION_POS["SIC"],
                         offset_sic // BLOCKSIZE, 8, n_episodes)

    total = offset_sic + (len(sic) if sic else 0)
    buf = bytearray(total)
    buf[0:4096] = header
    buf[offset_str:offset_str + len(str_blob)] = str_blob
    buf[offset_pil:offset_pil + len(pil)] = pil
    buf[offset_adc:offset_adc + len(adc)] = adc
    if int16:
        buf[offset_data:offset_data + data_bytes] = raw.tobytes()
    else:
        buf[offset_data:offset_data + data_bytes] = flat.tobytes()
    if sic:
        buf[offset_sic:offset_sic + len(sic)] = sic

    with open(path, "wb") as f:
        f.write(buf)
    return path