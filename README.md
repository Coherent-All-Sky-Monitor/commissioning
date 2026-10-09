# Coherent All-Sky Monitor (CASM) - Commissioning Workspace

I will record all of CASM hardware commissioning data and files in this repository. This workspace contains automation/data acquisition scripts, data, and reference manuals for characterizing receiver components, including Low Noise Amplifiers (LNAs), backend boards and antennas.

---

## Setup

The only requirement is [uv](https://docs.astral.sh/uv/), which installs the right Python version and the exact package versions pinned in `uv.lock`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The measurement scripts in the repo root (`./lna_sparams.sh`, `./bac_sparams.sh`) use uv automatically. To run any other script in the repo, prefix it with `uv run`, e.g. `uv run python tools/vna/test_vna_scpi.py`. `uv run` works from any folder inside the repo.

---
# as of July 20

## S-Parameter Data

All S-Parameter measurement sweeps performed via our automation tools are compiled dynamically:

* **[LNA Plot & Touchstone Data Viewer](./LNA/data_viewer.md)**: view plots and download raw `.s2p` Touchstone files.
* **[LNA Diagnostic Log](./LNA/diagnostics.md)**: Displays the cumulative log parameters (S11, S21, S12, S22, current draw, and timestamp).
* **[Backboard Plot & Touchstone Data Viewer](./BB/data_viewer.md)**: view plots and download raw `.s2p` Touchstone files.
* **[Backboard Diagnostic Log](./BB/diagnostics.md)**: Displays the cumulative log parameters (S11, S21, S12, S22, current draw, and timestamp).

---

### 1. Low Noise Amplifiers (LNA)
The receiver LNAs are characterized for both S-parameters (using a LibreVNA) and Noise Figures.
- **[LNA Workspace Overview](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA)**: Main folder for LNA test setups.
- **[S-Parameters Workspace (`LNA/s_params`)](./LNA/s_params/)**:
  - Measure with `./lna_sparams.sh` (uses the shared [S-Parameter tool](./tools/vna/README.md))
  - **[Plots Directory (`LNA/s_params/plots`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/s_params/plots)**: Directory containing plots.
  - **[Touchstone Directory (`LNA/s_params/touchstone`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/s_params/touchstone)**: Raw `.s2p` Touchstone data files.
- **[Noise Figure Workspace (`LNA/noise_figure`)](./LNA/noise_figure/)**:
  - Acquire with `./lna_nf_measure.sh`, analyze with `./lna_nf.sh -b <name>` or `./lna_nf.sh --all` (uses the shared [Noise Figure tools](./tools/noise_figure/README.md))
  - **[Noise Figure Results (`nf_log.csv`)](./LNA/noise_figure/nf_log.csv)**: In-band noise figure, noise temperature and gain for every measured LNA.
  - **[Modified LNA Data Directory (`LNA/noise_figure/data/modified/`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/modified)**
  - **[Unmodified LNA Data Directory (`LNA/noise_figure/data/unmodified/`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/unmodified)**

### 2. Backboards (BB)
- **[Backboard Workspace Overview](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/BB)**: Main folder for backboard test setups.
- **[S-Parameters Workspace (`BB/s_params`)](./BB/s_params/)**: Full 2-port S-parameters of the backboards (`BAC#####P1/P2`).
  - Measure with `./bac_sparams.sh` (uses the shared [S-Parameter tool](./tools/vna/README.md))
  - **[Plots Directory (`BB/s_params/plots`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/BB/s_params/plots)**: Directory containing plots.
  - **[Touchstone Directory (`BB/s_params/touchstone`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/BB/s_params/touchstone)**: Raw `.s2p` Touchstone data files.
- **[Noise Figure Workspace (`BB/noise_figure`)](./BB/noise_figure/)**: Y-factor noise figure with a calibrated noise source (ENR table).
  - Acquire with `./bac_nf_measure.sh`, analyze with `./bac_nf.sh -b BAC#####P#` or `./bac_nf.sh --all` (uses the shared [Noise Figure tools](./tools/noise_figure/README.md))
  - **[Noise Figure Results (`nf_log.csv`)](./BB/noise_figure/nf_log.csv)**: In-band noise figure, noise temperature and gain for every measured backboard.
  - **[Backboard Data Directory (`BB/noise_figure/data/`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/BB/noise_figure/data)**
  - **[Backboard Plots Directory (`BB/noise_figure/plots/`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/BB/noise_figure/plots)**

### 3. Antenna
- **[Antenna Workspace (`Antenna`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/Antenna)**:

### 4. Measurement Tools
- **[S-Parameter Tool (`tools/vna`)](./tools/vna/README.md)**: LibreVNA CLI shared by all devices. Explains the calibration workflow, electrical delay de-embedding math, and per-machine calibration instances.
- **[Noise Figure Tools (`tools/noise_figure`)](./tools/noise_figure/README.md)**: Siglent spectrum analyzer acquisition and Y-factor noise figure analysis, with hot/cold loads (LNAs) or an ENR noise source (backboards).

### 5. Instrument Manuals
- **[Reference Guides (`instrument_manuals`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/instrument_manuals)**:
  - **[LibreCAL Manuals (`instrument_manuals/libreCAL`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/instrument_manuals/libreCAL)**: PDF manuals detailing the electronic calibration standard and SCPI interfaces.
  - **[LibreVNA Manuals (`instrument_manuals/libreVNA`)](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/instrument_manuals/libreVNA)**: Programming and setup manual for the Vector Network Analyzer hardware.

---
