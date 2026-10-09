# Noise Figure Tools (Y-Factor)

Python tools for acquiring hot/cold noise spectra from a Siglent SSA3032X Plus spectrum analyzer and computing noise temperature, noise figure and gain with the Y-factor method. Code lives here; measurement data lives in each device's noise-figure workspace.

| Device | `--device` | Workspace | Hot / cold reference |
|---|---|---|---|
| Low Noise Amplifier | `lna` | [`LNA/noise_figure/`](../../LNA/noise_figure/README.md) | Room-temperature load / load in liquid nitrogen |
| Backboard | `bac` | [`BB/noise_figure/`](../../BB/noise_figure/README.md) | Noise source on / off, with its ENR table |

New device types are added to the `DEVICES` table at the top of `nf.py`.

## Running

From the repo root (uses [uv](https://docs.astral.sh/uv/)):

```bash
./lna_nf_measure.sh                      # LNA: acquire a hot or cold trace from the spectrum analyzer
./lna_nf.sh -b lna173 --save-plot        # LNA: analyze one measurement
./lna_nf.sh --all                        # LNA: re-analyze every measurement, save all plots, refresh the log
./bac_nf_measure.sh                      # Backboard: acquire a source-on/off trace or the analyzer calibration
./bac_nf.sh -b BAC00018P1 --save-plot    # Backboard: analyze one measurement
./bac_nf.sh --all                        # Backboard: re-analyze everything
```

These are shortcuts for `uv run python tools/noise_figure/<script>.py --device lna|bac`.

## Hot/cold reference methods

Both methods use the same Y-factor formula, Te = (Th − Y·Tc)/(Y − 1); they differ in where Th and Tc come from.

- **Loads (`lna`)**: physical loads at known temperatures, Th = 296.85 K (room temperature) and Tc = 77 K (liquid nitrogen) by default.
- **ENR noise source (`bac`)**: hot is the noise source switched on, Th(f) = 290 K × (10^(ENR(f)/10) + 1), with ENR interpolated (in dB) from the source's table; cold is the source switched off, at room temperature (Tc = 296.85 K by default, `--tc` to override).

ENR tables live in `enr/` as CSV files with `freq_mhz,enr_db` columns (`#` lines are comments). [`enr/ebay_5p5dB.csv`](./enr/ebay_5p5dB.csv) is currently a **placeholder** at the nominal 5.5 dB; the analysis prints a warning until the word PLACEHOLDER is removed from it. `--enr-table <file>` uses a different table for one run.

For the ENR method, first record an **analyzer calibration** (noise source straight into the analyzer) with `./bac_nf_measure.sh`. It is saved as `cal_hot_.npz` / `cal_cold_.npz` in the data subfolder and used to remove the analyzer's own noise from every measurement in that subfolder.

Each workspace holds:
- `data/<subfolder>/<base>_hot_.npz`, `<base>_cold_.npz`: raw traces, grouped into subfolders (e.g. `modified/`, `unmodified/`).
- `plots/<subfolder>/<base>_nf.png`: analysis plots, mirroring the `data/` layout.
- `nf_log.csv`: in-band results for every analyzed measurement, one row per base name (re-running a measurement replaces its row).

## Scripts

### 1. `nf.py`
Computes Y-factor noise figure, receiver noise temperature (Te) and transducer gain from hot/cold spectrum data.
- **Y-Factor Method**: Computes the Y-factor ratio and extracts noise temperature Te = (Th − Y·Tc)/(Y − 1) and noise figure NF = 10·log10(1 + Te/290 K).
- **Statistical Summary**: In-band (390–483 MHz) median, mean and standard deviation of gain, Te and noise figure.
- **Plot Generation**: 2x2 plots of input power spectra, noise figure, transducer gain and Te with band shading.
- **Load temperatures**: `--th`/`--tc` if given, else a `load_temp_k` recorded in the trace metadata, else the device default.
- **De-embedding**: If `cal_hot.npz` / `cal_cold.npz` exist next to the measurement, the instrument's own noise contribution is removed (DUT-only mode).
- **CLI Options**:
  - `-b`, `--base <base_name>`: Measurement base name (e.g. `lna173`). Searched for anywhere under the workspace's `data/` folder.
  - `--all`: Analyze every hot/cold pair in the workspace (saves plots, no windows).
  - `-I`, `--interactive`: Prompt for base name, load temperatures, smoothing and plot saving.
  - `--tc <temp_k>` / `--th <temp_k>`: Cold / hot load physical temperature in Kelvin (`--th` is ignored for noise-source devices).
  - `--enr-table <file>`: Use a different ENR table (noise-source devices only).
  - `--no-smooth`: Plot raw traces instead of smoothed ones.
  - `--save-plot`: Save the plot to the workspace's `plots/` folder.
  - `--no-show`: Don't open the plot window.

### 2. `spectrum_analyzer.py`
Automated VISA acquisition interface for Siglent SSA3032X Plus spectrum analyzers.
- **Acquisition Modes**: Single trace or Python-side trace averaging (power domain mW or logarithmic dBm).
- **Instrument Setup**: Configures frequency span (fstart, fstop), resolution bandwidth (RBW), detector, preamplifier state and RF attenuation.
- **Data Export**: Saves `.npz` files into `<workspace>/data/<subfolder>/` with JSON metadata containing ISO timestamps and instrument settings.
- **CLI Workflow & Prompts**:
  - **Measurement Mode**: `1` for single trace or `2` for averaged trace.
  - **VISA Resource Selection**: Pick the connected instrument from the PyVISA resource manager.
  - **Instrument Parameters**: Start/stop frequency, RBW, detector mode (`POS`, `NEG`, `SAMP`, `AVER`), preamp (`y/n`), attenuation (dB), trace count (`n_avg`) and averaging mode (`power` vs `dbm`).
  - **Data Designation**: Base name, data subfolder, measurement condition and overwrite flag. For backboards the base name is built from the backboard number and polarization (`BAC#####P1/P2`), the condition is noise source `on`/`off`, and you can choose to record the analyzer calibration instead.

### 3. `utils.py`
Core utility module supporting instrument interaction and data serialization.
- `SpectrumAnalyzer`: Class wrapper for PyVISA SCPI communication, trace query auto-detection and synchronization.
- **Power Conversions**: `dbm_to_mw` and `mw_to_dbm` for linear power averaging.
- **File Management**: `save_npz` handles file creation and metadata embedding.
