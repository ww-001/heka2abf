"""Command-line interface: heka2abf <input.dat> [options]"""

import argparse
import sys

from .convert import convert_dat
from .reader import load_dat


def _cmd_inspect(dat_path):
    series = load_dat(dat_path)
    print("HEKA bundle %s:" % dat_path)
    print("  %d series total" % len(series))
    import heka_reader
    b = heka_reader.Bundle(dat_path)
    print("  catalog items:", list(b.catalog.keys()))
    for ser in series:
        n_sw = len(ser.sweeps)
        chans = ser.all_adc_channels()
        print("  group %d series %d '%s': %d sweep(s), ADC channels %s, "
              "%.6g s/point" %
              (ser.group_idx + 1, ser.series_idx + 1, ser.label, n_sw, chans,
               ser.sampling_interval_s() if ser.sweeps else 0))
        if ser.sweeps:
            sw = ser.sweeps[0]
            for ch in sw.channels:
                print("      trace adc=%d '%s' unit=%s points=%d" %
                      (ch.adc_channel, ch.label, ch.unit, len(ch)))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="heka2abf",
        description="Convert HEKA PatchMaster .dat files to ABF2 files "
                    "(readable by Clampfit).")
    p.add_argument("dat", help="input HEKA .dat file")
    p.add_argument("--out-dir", "-o", default=".",
                   help="output directory (default: current directory)")
    p.add_argument("--one-file-per-channel", action="store_true",
                   help="write one ABF per ADC channel instead of one "
                        "per series")
    p.add_argument("--mode", choices=["auto", "episodic", "gapfree"],
                   default="auto",
                   help="acquisition mode: auto (default), episodic, or "
                        "gapfree (e.g. --mode episodic keeps single-sweep "
                        "series as episodic files)")
    p.add_argument("--inspect", action="store_true",
                   help="only print the structure of the .dat bundle and exit")
    args = p.parse_args(argv)

    if args.inspect:
        return _cmd_inspect(args.dat)

    written = convert_dat(args.dat, out_dir=args.out_dir,
                          one_file_per_channel=args.one_file_per_channel,
                          mode=args.mode)
    for w in written:
        print("wrote %s" % w)
    print("%d ABF2 file(s) written to %s" % (len(written), args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())