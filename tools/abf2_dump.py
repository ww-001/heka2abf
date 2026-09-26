"""Dump the structure of a real ABF2 file (header sections + data section info).

Use this to study what Clampfit/pClamp writes, and to cross-check the files
written by heka2abf.abf2writer.

Usage:  python tools/abf2_dump.py <file.abf>
"""

import struct
import sys


def u8(b, o): return b[o]
def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]
def i16(b, o): return struct.unpack_from("<h", b, o)[0]
def f32(b, o): return struct.unpack_from("<f", b, o)[0]
def f64(b, o): return struct.unpack_from("<d", b, o)[0]


def cstr(b, start, length):
    raw = b[start:start + length]
    end = raw.find(b"\x00")
    if end == -1:
        end = length
    return raw[:end].decode("ascii", errors="replace")


def dump_fb(h):
    print("== FB (File Section) ==")
    print("  signature       :", cstr(h, 0, 4))
    print("  version bytes   :", list(h[4:8]))
    print("  uFileInfoSize   :", u32(h, 8))
    print("  lActualEpisodes :", u32(h, 12))
    print("  uFileStartDate  :", u32(h, 16))
    print("  uFileStartTimeMS:", u32(h, 20))
    print("  uStopwatchTime  :", u32(h, 24))
    print("  nFileType       :", u16(h, 28))
    print("  nDataFormat     :", u16(h, 30), "(0=int16, 1=float32)")
    print("  nSimultaneousScan:", u16(h, 32))
    print("  nCRCEnable      :", u16(h, 34))
    print("  uFileCRC        :", hex(u32(h, 36)))
    print("  uFileGUID       :", h[40:56].hex())
    print("  uCreatorVersion :", list(h[56:60]))
    print("  uCreatorNameIndex:", u32(h, 60))


SECTION_LABELS = {
    76: "PIL", 92: "ADC", 108: "DAC", 124: "EPE", 140: "EPC",
    156: "TAG", 172: "LTC", 188: "SMT", 204: "NDC", 220: "STR",
    236: "DATA", 252: "UPL", 268: "PII", 284: "PRT", 300: "???",
    316: "SIC",
}


def dump_section_index(h):
    print("\n== Section index (16-byte descriptors from byte 76) ==")
    for pos in range(76, 332, 16):
        block, bytes_, count = struct.unpack_from("<III", h, pos)
        if block or bytes_ or count:
            print("  %-5s @%3d  block=%4d (%7dB)  size/entry=%6d  count=%d" %
                  (SECTION_LABELS.get(pos, "?"), pos, block, block * 512,
                   bytes_, count))


def dump_pil(h, b):
    """PIL (protocol) section. Entry layout follows pyabf/abf2/protocolSection.py"""
    print("\n== PIL (Protocol Section) ==")
    o = 0
    print("  nOperationMode        :", i16(b, o)); o += 2
    print("  fADCSequenceInterval  : %.6f us" % f32(b, o)); o += 4
    print("  bEnableFileCompression:", b[o]); o += 4
    _ = i32(b, o); o += 4  # uFileCompressionRatio
    print("  fSynchTimeUnit        :", f32(b, o)); o += 4
    print("  fSecondsPerRun        :", f32(b, o)); o += 4
    print("  lNumSamplesPerEpisode :", i32(b, o)); o += 4
    print("  lPreTriggerSamples    :", i32(b, o)); o += 4
    print("  lEpisodesPerRun       :", i32(b, o)); o += 4
    print("  lRunsPerTrial         :", i32(b, o)); o += 4
    print("  lNumberOfTrials       :", i32(b, o)); o += 4
    print("  nAveragingMode        :", i16(b, o)); o += 2
    print("  nUndoRunCount         :", i16(b, o)); o += 2
    print("  nFirstEpisodeInRun    :", i16(b, o)); o += 2
    print("  fTriggerThreshold     :", f32(b, o)); o += 4
    print("  nTriggerSource        :", i16(b, o)); o += 2
    print("  nTriggerAction        :", i16(b, o)); o += 2
    print("  nTriggerPolarity      :", i16(b, o)); o += 2
    print("  fScopeOutputInterval  :", f32(b, o)); o += 4
    print("  fEpisodeStartToStart  : %.6f s" % f32(b, o)); o += 4
    print("  fRunStartToStart      :", f32(b, o)); o += 4
    print("  lAverageCount         :", i32(b, o)); o += 4
    print("  fTrialStartToStart    :", f32(b, o)); o += 4
    print("  nAutoTriggerStrategy  :", i16(b, o)); o += 2
    print("  fFirstRunDelayS       :", f32(b, o)); o += 4
    print("  nChannelStatsStrategy :", i16(b, o)); o += 2
    print("  lSamplesPerTrace      :", i32(b, o)); o += 4
    print("  lStartDisplayNum      :", i32(b, o)); o += 4
    print("  lFinishDisplayNum     :", i32(b, o)); o += 4
    print("  nShowPNRawData        :", i16(b, o)); o += 2
    print("  fStatisticsPeriod     :", f32(b, o)); o += 4
    print("  lStatisticsMeasurements:", i32(b, o)); o += 4
    print("  nStatisticsSaveStrategy:", i16(b, o)); o += 2
    print("  fADCRange             :", f32(b, o)); o += 4
    print("  fDACRange             :", f32(b, o)); o += 4
    print("  lADCResolution        :", i32(b, o)); o += 4
    print("  lDACResolution        :", i32(b, o)); o += 4
    print("  nExperimentType       :", i16(b, o)); o += 2
    print("  nManualInfoStrategy   :", i16(b, o)); o += 2
    print("  nCommentsEnable       :", i16(b, o)); o += 2
    print("  lFileCommentIndex     :", i32(b, o)); o += 4
    print("  nAutoAnalyseEnable    :", i16(b, o)); o += 2
    print("  nSignalType           :", i16(b, o)); o += 2
    print("  nDigitalEnable        :", i16(b, o)); o += 2
    print("  nActiveDACChannel     :", i16(b, o)); o += 2
    print("  nDigitalHolding       :", i16(b, o)); o += 2
    print("  nDigitalInterEpisode  :", i16(b, o)); o += 2
    print("  nDigitalDACChannel    :", i16(b, o)); o += 2
    print("  nDigitalTrainActiveLogic:", i16(b, o)); o += 2
    print("  nStatsEnable          :", i16(b, o)); o += 2
    print("  nStatisticsClearStrategy:", i16(b, o)); o += 2
    print("  nLevelHysteresis      :", i16(b, o)); o += 2
    print("  lTimeHysteresis       :", i32(b, o)); o += 4
    print("  nAllowExternalTags    :", i16(b, o)); o += 2
    print("  nAverageAlgorithm     :", i16(b, o)); o += 2
    print("  fAverageWeighting     :", f32(b, o)); o += 4
    print("  nUndoPromptStrategy   :", i16(b, o)); o += 2
    print("  nTrialTriggerSource   :", i16(b, o)); o += 2
    print("  nStatisticsDisplayStrategy:", i16(b, o)); o += 2
    print("  nExternalTagType      :", i16(b, o)); o += 2
    print("  nScopeTriggerOut      :", i16(b, o)); o += 2
    print("  nLTPType              :", i16(b, o)); o += 2
    print("  nAlternateDACOutputState:", i16(b, o)); o += 2
    print("  nAlternateDigitalOutputState:", i16(b, o)); o += 2
    print("  fCellID               :", [f32(b, o + 4 * i) for i in range(3)]); o += 12
    print("  nDigitizerADCs        :", i16(b, o)); o += 2
    print("  nDigitizerDACs        :", i16(b, o)); o += 2
    print("  nDigitizerTotalDigitalOuts:", i16(b, o)); o += 2
    print("  nDigitizerSynchDigitalOuts:", i16(b, o)); o += 2
    print("  nDigitizerType        :", i16(b, o)); o += 2
    print("  PIL entry size        :", o)


def dump_adc(h, b, count):
    print("\n== ADC Section (%d channels, entry size 82) ==" % count)
    for i in range(count):
        e = b[i * 82:(i + 1) * 82]
        print("  ch%d: adcNum=%d telegEnable=%d telegInstrument=%d additGain=%g"
              % (i, i16(e, 0), i16(e, 2), i16(e, 4), f32(e, 6)))
        print("       pToLMap=%d samplingSeq=%d progGain=%g dispAmp=%g dispOff=%g"
              % (i16(e, 24), i16(e, 26), f32(e, 28), f32(e, 32), f32(e, 36)))
        print("       instrScale=%g instrOff=%g signalGain=%g signalOff=%g"
              % (f32(e, 40), f32(e, 44), f32(e, 48), f32(e, 52)))
        print("       lowpass=%g highpass=%g lpType=%d hpType=%d"
              % (f32(e, 56), f32(e, 60), e[64], e[65]))
        print("       postLP=%g enabledPN=%d statsPol=%d nameIdx=%d unitIdx=%d"
              % (f32(e, 66), e[71], i16(e, 72), u32(e, 74), u32(e, 78)))


def dump_dac(h, b, count):
    print("\n== DAC Section (%d channels, entry size 132) ==" % count)
    for i in range(count):
        e = b[i * 132:(i + 1) * 132]
        print("  dac%d: num=%d hold=%g scale=%g calibF=%g calibO=%g nameIdx=%d unitIdx=%d"
              % (i, i16(e, 0), f32(e, 12), f32(e, 8), f32(e, 16), f32(e, 20),
                 u32(e, 24), u32(e, 28)))


def dump_str(h, b, count):
    print("\n== STR (Strings) Section (%d entries, entrySize=%d) ==" %
          (count, len(b) // count if count else 0))
    if not count:
        return
    entry_size = len(b) // count
    raw0 = b[:entry_size]
    # replicate pyABF's _indexedStrings logic
    idx = raw0.rfind(b"\x00\x00")
    part = raw0[idx:]
    parts = [x.decode("ascii", errors="replace").strip()
             for x in part.split(b"\x00")[1:]]
    print("  indexedStrings:", parts)
    for i in range(count):
        s = b[i * entry_size:(i + 1) * entry_size]
        txt = s.split(b"\x00")[0].decode("ascii", errors="replace")
        print("  str[%d] head: %r" % (i, txt[:60]))


def dump_data(h, b, count):
    print("\n== DATA section: block=%d nbytes=%d count=%d (float32=%d points)" %
          (u32(h, 236), u32(h, 240), i32(h, 244), count // 4))


def dump_sic(h, b, count):
    print("\n== SIC (SynchArray) Section (%d entries, entry size 8) ==" % count)
    for i in range(count):
        e = b[i * 8:(i + 1) * 8]
        print("  entry %d: lStart=%d lLength=%d" % (i, i32(e, 0), i32(e, 4)))


def main(path):
    with open(path, "rb") as f:
        data = f.read()
    header = data[:4096]
    dump_fb(header)
    dump_section_index(header)

    entries = {}
    for pos in range(76, 332, 16):
        block, nbytes, count = struct.unpack_from("<III", header, pos)
        if block:
            entries[pos] = (block, nbytes, count)

    def sec(pos):
        block, nbytes, count = entries.get(pos, (0, 0, 0))
        start = block * 512
        return data[start:start + nbytes], count, start

    pil_b, pil_n, _ = sec(76)
    if pil_b:
        dump_pil(header, pil_b)
    adc_b, adc_n, _ = sec(92)
    if adc_b:
        dump_adc(header, adc_b, adc_n)
    dac_b, dac_n, _ = sec(108)
    if dac_b:
        dump_dac(header, dac_b, dac_n)
    str_b, str_n, _ = sec(220)
    if str_b:
        dump_str(header, str_b, str_n)
    sic_b, sic_n, _ = sec(316)
    if sic_b:
        dump_sic(header, sic_b, sic_n)
    data_b, data_n, data_start = sec(236)
    if data_b:
        dump_data(header, data_b, data_n)
        print("  data section starts at byte", data_start)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])