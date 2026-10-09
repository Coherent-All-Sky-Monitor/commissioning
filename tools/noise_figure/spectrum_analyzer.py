"""
Spectrum Analyzer VISA Control Tool (Siglent SSA3032X Plus)
Single trace + Averaged trace only

- Choose mode: single or average
- Optionally set fstart/fstop/RBW/detector/preamp/attenuation
- Reads back and prints settings BEFORE acquisition (and again after setup)
- Forces instrument internal averaging OFF, forces trigger immediate
- Saves NPZ: <workspace>/data/<group>/<base>_<hot|cold>_.npz  (no timestamp in filename)

Usage:
    python spectrum_analyzer.py --device lna
"""

import argparse
from pathlib import Path

from nf import CAL_BASE, DEVICES, REPO_ROOT
from utils import (
    SpectrumAnalyzer,
    pick_resource,
    prompt_sa_settings,
    acquire_averaged_trace,
    save_npz,
    utc_timestamp_iso,
)


def prompt_measurement_mode():
    print("\nSelect measurement mode:")
    print("  [1] Single trace")
    print("  [2] Averaged trace")
    while True:
        s = input("Enter choice (1-2): ").strip()
        if s == "1":
            return "single"
        if s == "2":
            return "average"
        print("Invalid choice. Please enter 1 or 2.")


def prompt_hot_cold(noise_source=False):
    """Hot/cold load, or noise source on/off (saved as hot/cold)."""
    if noise_source:
        while True:
            s = input("Noise source state (on/off): ").strip().lower()
            if s in ("on", "off"):
                return "hot" if s == "on" else "cold"
            print("Invalid entry. Please type 'on' or 'off'.")
    while True:
        s = input("Measurement condition (hot/cold): ").strip().lower()
        if s in ("hot", "cold"):
            return s
        print("Invalid entry. Please type 'hot' or 'cold'.")


def prompt_part_number(prefix, label):
    """Build <prefix><5 digits>P<polarization>, e.g. BAC00018P1."""
    while True:
        s = input(f"{label} number [00000-99999]: ").strip()
        if s.isdigit() and 0 <= int(s) <= 99999:
            num = int(s)
            break
        print("Must be a number between 0 and 99999.")
    while True:
        pol = input("Polarization [1 or 2]: ").strip()
        if pol in ("1", "2"):
            break
        print("Please type 1 or 2.")
    return f"{prefix}{num:05d}P{pol}"


def prompt_base(device):
    """Measurement base name: free text, or a part number for devices with a prefix."""
    if device["method"] == "enr":
        print("\nWhat is connected to the spectrum analyzer?")
        print(f"  [1] {device['label']} (noise source -> {device['label']} -> analyzer)")
        print("  [2] Analyzer calibration (noise source straight into the analyzer)")
        while True:
            s = input("Enter choice (1-2): ").strip()
            if s == "2":
                return CAL_BASE
            if s == "1":
                break
            print("Invalid choice. Please enter 1 or 2.")
    if device["part_prefix"]:
        return prompt_part_number(device["part_prefix"], device["label"])
    return input("\nEnter base filename (no extension): ").strip()


def prompt_group(data_dir: Path):
    """Pick the data subfolder (e.g. modified / unmodified) to save into."""
    existing = sorted(p.name for p in data_dir.iterdir() if p.is_dir()) if data_dir.exists() else []
    hint = f" (existing: {', '.join(existing)})" if existing else ""
    return input(f"Data subfolder under {data_dir.relative_to(REPO_ROOT)}/{hint} [blank = data/ itself]: ").strip()


def main():
    parser = argparse.ArgumentParser(description="Spectrum analyzer hot/cold trace acquisition.")
    parser.add_argument("--device", choices=sorted(DEVICES), default="lna", help="Device workspace to save into.")
    args = parser.parse_args()
    device = DEVICES[args.device]
    data_dir = REPO_ROOT / device["workspace"] / "data"
    noise_source = device["method"] == "enr"

    print("Spectrum Analyzer Control Tool")
    print("=" * 40)
    print(f"Saving to: {data_dir}")

    mode = prompt_measurement_mode()

    print("\n=== Instrument Connection ===")
    resource = pick_resource()
    sa = SpectrumAnalyzer(resource)

    try:
        # Readback BEFORE changes
        sa.print_settings("Current instrument settings (readback)")

        # Ask user what to change
        print("\n=== Measurement Configuration ===")
        settings = prompt_sa_settings(include_avg=(mode == "average"))

        # Apply requested settings
        sa.setup(
            fstart=settings["fstart"],
            fstop=settings["fstop"],
            rbw=settings["rbw"],
            detector=settings["detector"],
            preamp=settings["preamp"],
            att=settings["att"],
        )

        # Force analyzer internal averaging OFF + trigger immediate
        sa.force_python_averaging(verbose=True)

        # Readback AFTER setup
        final_rb = sa.print_settings("Final instrument settings (readback)")

        go = (input("\nProceed with acquisition? [Y/n]: ").strip().lower() or "y")
        if go != "y":
            print("Aborted.")
            return

        base = prompt_base(device)
        if not base:
            print("No base filename entered. Aborting.")
            return

        out_dir = data_dir / prompt_group(data_dir)
        if base == CAL_BASE:
            print(f"Calibration is used for every measurement in {out_dir.relative_to(REPO_ROOT)}/")
        hot_cold = prompt_hot_cold(noise_source)
        overwrite = (input("Overwrite existing file if present? [y/N]: ").strip().lower() == "y")

        if mode == "single":
            freq_hz, trace_dbm = sa.acquire_trace()
            meta = {
                "mode": "single",
                "hot_cold": hot_cold,
                "device": args.device,
                "noise_source": ({"hot": "on", "cold": "off"}[hot_cold] if noise_source else None),
                "enr_table": device.get("enr_table"),
                "timestamp_iso": utc_timestamp_iso(),
                "instrument_readback": final_rb,
                "note": "Trace is displayed spectrum trace (not complex IQ).",
            }
            save_npz(base, hot_cold, freq_hz, trace_dbm, meta, overwrite=overwrite, out_dir=out_dir)

        else:
            n_avg = settings["n_avg"] or 4
            avg_mode = settings["avg_mode"] or "power"
            print(f"\nAveraging {n_avg} traces (avg_mode={avg_mode})...")

            freq_hz, trace_dbm = acquire_averaged_trace(sa, n_avg=n_avg, avg_mode=avg_mode)

            meta = {
                "mode": "average",
                "hot_cold": hot_cold,
                "device": args.device,
                "noise_source": ({"hot": "on", "cold": "off"}[hot_cold] if noise_source else None),
                "enr_table": device.get("enr_table"),
                "timestamp_iso": utc_timestamp_iso(),
                "n_avg": n_avg,
                "avg_mode": avg_mode,
                "instrument_readback": final_rb,
                "note": "Trace is displayed spectrum trace (not complex IQ).",
            }
            save_npz(base, hot_cold, freq_hz, trace_dbm, meta, overwrite=overwrite, out_dir=out_dir)

    finally:
        sa.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()