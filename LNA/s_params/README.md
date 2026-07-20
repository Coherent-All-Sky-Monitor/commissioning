# LNA S-Parameter Measurement Tool (LibreVNA)

This directory contains a robust Command-Line Interface (CLI) tool for automating the characterization of Low Noise Amplifiers (LNAs) using a LibreVNA and LibreCAL electronic calibration module.

## Files & Directories
- `lna_sparams.py`: The main automation script with a Rich CLI.
- `libreVNA.py`: A helper class that provides a TCP socket SCPI interface to the LibreVNA-GUI.
- `cal_manager.py`: Manages calibration instances, port extensions, and mathematical de-embedding.
- `cal_files/`: Directory where you must save your LibreVNA GUI base `.cal` files.
- `touchstone/`: Directory where generated `.s2p` Touchstone files are saved.
- `plots/`: Directory where generated high-resolution (300 DPI) 2x4 magnitude and Smith Chart plots are saved.
- `lna_diagnostic_log.csv`: The cumulative log of diagnostic measurements at the specified diagnostic frequency.
- `cal_instances.json`: Automatically generated database that stores your base calibrations and adapter port extensions.

## Requirements
- **Hardware:** LibreVNA and LibreCAL connected via USB.
- **Software:** 
  - LibreVNA-GUI running with the SCPI server enabled (default port `19542`).
  - Python 3 with the following packages:
    ```bash
    pip install numpy matplotlib scikit-rf rich
    ```

## Usage

1. Launch the **LibreVNA-GUI**. Ensure the SCPI server is enabled in `Window -> Preferences -> General`.
2. Do a one-time GUI calibration and save it to `LNA/s_params/cal_files/`.
3. Run the measurement script:
   ```bash
   python lna_sparams.py
   ```
4. Follow the interactive prompts to:
   - **Calibration Instance:** Pick an existing setup or create a new one. When creating a new one, the script will let you select a base `.cal` file and can automatically mathematically compute the electrical delay of any adapters by measuring an OPEN or SHORT.
   - **Verify:** Attach a verification standard (like a THRU). The script will immediately print a 4-panel LogMag and 4-panel Smith Chart directly into your terminal alongside numeric metrics to verify the calibration.
   - **Measure LNAs:** Enter the part number and current draw. The script will measure the device, strip out the adapter delay, save a Touchstone file, generate an A4-optimized high-res PNG, and log it to the CSV.

## Advanced Features
- **Auto-computed De-embedding:** The script uses NumPy phase unwrapping and linear regression to auto-compute adapter electrical delays exactly in picoseconds. This shift is mathematically applied to all S-parameters before export.
- **In-Terminal Diagnostics:** Injects the full-resolution matplotlib verification PNG (LogMag + Smith Charts) directly into your terminal window using standard iTerm2/Kitty inline image protocols, avoiding GUI popups and file clutter.
- **Print-Optimized PNGs:** Standard plots are rendered on a 2x4 grid (LogMag + `scikit-rf` Smith Charts) sized at `11.5x8.0` inches and 300 DPI, perfect for clean US Letter / A4 printing. Each plot is strictly labeled with the part number and a timestamp.
- **Smart Diagnostics:** Automatically checks for duplicate measurements, warns before overwriting CSV logs, and allows logging "SHORT" circuits.
