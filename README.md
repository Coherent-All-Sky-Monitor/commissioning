# Coherent All-Sky Monitor (CASM) - Commissioning Workspace

I will record all of CASM hardware commissioning data and files in this repository. This workspace contains automation/data acquisition scripts, data, and reference manuals for characterizing receiver components, including Low Noise Amplifiers (LNAs), backend boards and antennas.

---
# as of July 20

## LNA S-Parameter Data

All S-Parameter measurement sweeps performed via our automation tools are compiled dynamically:

* **[LNA Plot & Touchstone Data Viewer](./LNA/lna_data)**: view plots and download raw `.s2p` Touchstone files.
* **[LNA Diagnostic Log](./LNA/lna_diagnostics)**: Displays the cumulative log parameters (S11, S21, S12, S22, current draw, and timestamp).

---

### 1. Low Noise Amplifiers (LNA)
The receiver LNAs are characterized for both S-parameters (using a LibreVNA) and Noise Figures.
- **[LNA Workspace Overview](./LNA/)**: Main folder for LNA test setups.
- **[S-Parameters Workspace (`LNA/s_params`)](./LNA/s_params/)**:
  - **[S-Parameters Guide (`LNA/s_params/README.md`)](./LNA/s_params/README.md)**: Explains the calibration workflow, electrical delay de-embedding math, and CLI automation.
  - **Main Script (`lna_sparams.py`)**: CLI measurement tool.
  - **[Plots Directory (`LNA/s_params/plots`)](./LNA/s_params/plots/)**: Directory containing plots.
  - **[Touchstone Directory (`LNA/s_params/touchstone`)](./LNA/s_params/touchstone/)**: Raw `.s2p` Touchstone data files.
- **[Noise Figure Workspace (`LNA/noise_figure`)](./LNA/noise_figure/)**:
  - **[Noise Figure Guide (`LNA/noise_figure/README.md`)](./LNA/noise_figure/README.md)**: Notes and setups for receiver noise measurements.
  - **[Modified LNA Data Directory (`LNA/noise_figure/data/modified/`)](./LNA/noise_figure/data/modified/)**
  - **[Unmodified LNA Data Directory (`LNA/noise_figure/data/unmodified/`)](./LNA/noise_figure/data/unmodified/)**

### 2. Antenna/ BB
- **[Antenna Workspace (`Antenna`)](./Antenna/)**:
  

### 3. Instrument Manuals
- **[Reference Guides (`instrument_manuals`)](./instrument_manuals/)**:
  - **[LibreCAL Manuals (`instrument_manuals/libreCAL`)](./instrument_manuals/libreCAL/)**: PDF manuals detailing the electronic calibration standard and SCPI interfaces.
  - **[LibreVNA Manuals (`instrument_manuals/libreVNA`)](./instrument_manuals/libreVNA/)**: Programming and setup manual for the Vector Network Analyzer hardware.

---
