# Coherent All-Sky Monitor (CASM) - Commissioning Workspace

I will record all of CASM hardware commissioning data and files in this repository. This workspace contains automation/data acquisition scripts, data, and reference manuals for characterizing receiver components, including Low Noise Amplifiers (LNAs), backend boards and antennas.

---

## Setup

Clone the repository and go into it:

```bash
git clone https://github.com/Coherent-All-Sky-Monitor/commissioning.git
cd commissioning
```

The only other requirement is [uv](https://docs.astral.sh/uv/), which installs the right Python version and the exact package versions pinned in `uv.lock`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Enable the repo's git hooks once (they keep the ensemble plots on the data viewer pages up to date when you commit new measurements; see `tools/vna/README.md`):

```bash
git config core.hooksPath .githooks
```

All commands below are run from the `commissioning` folder. To get the latest scripts and data later, run `git pull` there.

There are two ways to run things; both use the same environment in `.venv/`.

**1. Root scripts (nothing to set up).** The scripts in the repo root work from any folder. They use an activated virtual environment if there is one (including when launched with `uv run ./lna_sparams.sh`); otherwise they use uv, which creates `.venv/` on first use. Without uv they fall back to an existing `.venv/`.

| Script | Does |
|---|---|
| `./lna_sparams.sh`, `./bac_sparams.sh` | Measure LNA / backboard S-parameters |
| `./lna_nf_measure.sh`, `./bac_nf_measure.sh` | Acquire LNA / backboard noise-figure traces |
| `./lna_nf.sh`, `./bac_nf.sh` | Analyze LNA / backboard noise figure |

Any other script runs with a `uv run` prefix from any folder inside the repo, e.g. `uv run python tools/vna/test_vna_scpi.py`.

**2. A regular virtual environment.** Create (or update) `.venv/` and activate it, then call the Python scripts directly:

```bash
uv sync                      # create/update .venv with the pinned Python and packages
source .venv/bin/activate    # activate it (deactivate with `deactivate`)

python tools/vna/sparams.py --device lna            # same as ./lna_sparams.sh
python tools/noise_figure/nf.py --device bac --all  # same as ./bac_nf.sh --all
```

Re-run `uv sync` after pulling changes to `pyproject.toml` / `uv.lock`. To upgrade every package to its latest release, run `uv lock --upgrade && uv sync` and commit the new `uv.lock`.

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
