# S-Parameter Measurement Tool (LibreVNA)

This directory contains a Command-Line Interface (CLI) tool for automating full 2-port S-parameter characterization of CASM receiver components using a LibreVNA and LibreCAL electronic calibration module. The same tool measures every device type; only the part-number prefix and output folder change.

| Device | `--device` | Part number | Output folder |
|---|---|---|---|
| Low Noise Amplifier | `lna` | `LNA#####P1` / `P2` | [`LNA/s_params/`](../../LNA/s_params/README.md) |
| Backboard | `bac` | `BAC#####P1` / `P2` | [`BB/s_params/`](../../BB/s_params/README.md) |

New device types are added to the `DEVICES` table at the top of `sparams.py`.

## Files & Directories
- `sparams.py`: The main automation script with a Rich CLI.
- `libreVNA.py`: A helper class that provides a TCP socket SCPI interface to the LibreVNA-GUI.
- `cal_manager.py`: Manages calibration instances, port extensions, and mathematical de-embedding.
- `test_vna_scpi.py`: Minimal SCPI connectivity check.
- `local/` (git-ignored, created on first run): calibration state for **this machine only**.
  - `local/cal_files/`: Save your LibreVNA-GUI base `.cal` files here.
  - `local/cal_instances.json`: Your saved calibration instances (base `.cal` file + adapter port extensions), each with its creation time.

Each device's output folder holds:
- `touchstone/`: Generated `.s2p` Touchstone files.
- `plots/`: Generated high-resolution (300 DPI) magnitude and Smith Chart plots.
- `<prefix>_diagnostic_log.csv`: The cumulative log of diagnostic measurements at the diagnostic frequency.

## Calibrations are per machine
Calibrations depend on the VNA, cables and adapters on a given bench, and they drift over time, so they are not shared through git. Each machine keeps its own `local/` folder. When loading an instance the script shows how old it is.

So every measurement can be traced back to its calibration, the script records the calibration instance name, its creation time and the machine's hostname in each log row and in the header comments of each `.s2p` file.

## Requirements
- **Hardware:** LibreVNA and LibreCAL connected via USB.
- **Software:** 
  - LibreVNA-GUI running with the SCPI server enabled (default port `19542`).
  - [uv](https://docs.astral.sh/uv/). Python and all packages are pinned in the repo's `pyproject.toml` / `uv.lock` and installed automatically on first run.

## Usage

1. Launch the **LibreVNA-GUI**. Ensure the SCPI server is enabled in `Window -> Preferences -> General`.
2. Do a GUI calibration and save it to `tools/vna/local/cal_files/`.
3. Run the measurement script:
   ```bash
   ./lna_sparams.sh   # LNAs
   ./bac_sparams.sh   # Backboards
   ```
   These scripts in the repo root are shortcuts for `uv run python tools/vna/sparams.py --device lna|bac`.
4. Follow the interactive prompts to:
   - **Calibration Instance:** Pick an existing setup or create a new one. When creating a new one, the script will let you select a base `.cal` file and can automatically mathematically compute the electrical delay of any adapters by measuring an OPEN or SHORT.
   - **Verify:** Attach a verification standard (like a THRU). The script will immediately print a 4-panel LogMag and 4-panel Smith Chart directly into your terminal alongside numeric metrics to verify the calibration.
   - **Measure devices:** Enter the device number, polarization and current draw. The script will measure the device, strip out the adapter delay, save a Touchstone file, generate an A4-optimized high-res PNG, and log it to the CSV.

## Advanced Features
- **Auto-computed De-embedding:** The script uses NumPy phase unwrapping and linear regression to auto-compute adapter electrical delays exactly in picoseconds. This shift is mathematically applied to all S-parameters before export.
- **In-Terminal Diagnostics:** Injects the full-resolution matplotlib verification PNG (LogMag + Smith Charts) directly into your terminal window using standard iTerm2/Kitty inline image protocols, avoiding GUI popups and file clutter.
- **Print-Optimized PNGs:** Standard plots are rendered on a 2x4 grid (LogMag + `scikit-rf` Smith Charts) sized at `11.5x8.0` inches and 300 DPI, perfect for clean US Letter / A4 printing. Each plot is strictly labeled with the part number and a timestamp.
- **Smart Diagnostics:** Automatically checks for duplicate measurements, warns before overwriting CSV logs, and allows logging "SHORT" circuits.
