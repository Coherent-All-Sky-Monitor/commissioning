"""
Spectrum Analyzer VISA Control Tool (Siglent SSA3032X Plus)
Single trace + Averaged trace only

- Choose mode: single or average
- Optionally set fstart/fstop/RBW/detector/preamp/attenuation
- Reads back and prints settings BEFORE acquisition (and again after setup)
- Forces instrument internal averaging OFF, forces trigger immediate
- Saves NPZ: <base>_<hot|cold>_.npz  (no timestamp in filename)
"""

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


def prompt_hot_cold():
    while True:
        s = input("Measurement condition (hot/cold): ").strip().lower()
        if s in ("hot", "cold"):
            return s
        print("Invalid entry. Please type 'hot' or 'cold'.")


def main():
    print("Spectrum Analyzer Control Tool")
    print("=" * 40)

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

        base = input("\nEnter base filename (no extension): ").strip()
        if not base:
            print("No base filename entered. Aborting.")
            return

        hot_cold = prompt_hot_cold()
        overwrite = (input("Overwrite existing file if present? [y/N]: ").strip().lower() == "y")

        if mode == "single":
            freq_hz, trace_dbm = sa.acquire_trace()
            meta = {
                "mode": "single",
                "hot_cold": hot_cold,
                "timestamp_iso": utc_timestamp_iso(),
                "instrument_readback": final_rb,
                "note": "Trace is displayed spectrum trace (not complex IQ).",
            }
            save_npz(base, hot_cold, freq_hz, trace_dbm, meta, overwrite=overwrite)

        else:
            n_avg = settings["n_avg"] or 4
            avg_mode = settings["avg_mode"] or "power"
            print(f"\nAveraging {n_avg} traces (avg_mode={avg_mode})...")

            freq_hz, trace_dbm = acquire_averaged_trace(sa, n_avg=n_avg, avg_mode=avg_mode)

            meta = {
                "mode": "average",
                "hot_cold": hot_cold,
                "timestamp_iso": utc_timestamp_iso(),
                "n_avg": n_avg,
                "avg_mode": avg_mode,
                "instrument_readback": final_rb,
                "note": "Trace is displayed spectrum trace (not complex IQ).",
            }
            save_npz(base, hot_cold, freq_hz, trace_dbm, meta, overwrite=overwrite)

    finally:
        sa.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()