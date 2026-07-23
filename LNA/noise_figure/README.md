# Noise Figure Characterization & Measurement Suite

This directory contains the Python automation scripts, raw measurement data, and generated plots for characterizing Low Noise Amplifier (LNA) noise figures using the Y-Factor method.

## Contents of the directory

- [**`data/modified/`**](data/modified/): Raw NPZ dataset sweeps (`_hot_.npz`, `_cold_.npz`) for modified LNAs.
- [**`data/unmodified/`**](data/unmodified/): Raw NPZ dataset sweeps (`_hot_.npz`, `_cold_.npz`) for unmodified LNAs.
- [**`plots/modified/`**](plots/modified/): Generated Noise Figure plots for modified LNAs.
- [**`plots/unmodified/`**](plots/unmodified/): Generated Noise Figure plots for unmodified LNAs.

## Python Scripts & Utilities

### 1. `nf.py`
Computes Y-factor noise figure, system noise temperature (Tsys), and transducer gain profiles from hot/cold spectrum data.
- **Y-Factor Method**: Computes Y-factor ratio and extracts noise temperature Te and noise figure NF.
- **Statistical Summary**: Calculates in-band (390–483 MHz) median, mean, and standard deviation for Gain, Tsys, and Noise Figure.
- **Plot Generation**: Renders 2x2 multi-panel plots displaying input power spectra, Noise Figure, transducer gain, and system temperature with band shading.
- **CLI Options**:
  - `-b`, `--base <base_name>`: Base identifier for input measurement files (e.g., `lna173`). Expects `<base>_hot_.npz` and `<base>_cold_.npz` in the current folder. Mandatory when operating outside interactive mode.
  - `-I`, `--interactive`: Drop into interactive runtime mode with prompts for base name, load temperatures, trace vector smoothing, and plot saving.
  - `--tc <temp_k>`: Physical temperature of the cold standard load in Kelvin (default: `77.0` K for liquid nitrogen).
  - `--th <temp_k>`: Physical temperature of the hot standard load in Kelvin (default: `296.85` K for room temperature).
  - `--smooth`: Apply noise trace vector smoothing kernel (default: enabled).
  - `--no-smooth`: Deactivate noise trace vector smoothing to inspect raw unsmoothed spectra.
  - `--save-plot`: Automatically save the generated 2x2 multi-panel graphic to disk as `<base>_nf.png`.

  **CLI Usage Examples**:
  ```bash
  # Non-interactive calculation with plot saved to disk
  python nf.py -b lna173 --save-plot

  # Custom hot/cold temperatures with raw (unsmoothed) traces
  python nf.py -b lna174mod --tc 77.0 --th 295.5 --no-smooth --save-plot

  # Interactive prompt mode
  python nf.py -I
  ```

### 2. `spectrum_analyzer.py`
Automated VISA acquisition interface for Siglent SSA3032X Plus spectrum analyzers.
- **Acquisition Modes**: Supports single trace acquisition and Python-side trace averaging (power domain mW or logarithmic dBm).
- **Instrument Setup**: Configures frequency span (fstart, fstop), resolution bandwidth (RBW), detector, preamplifier state, and RF attenuation.
- **Data Export**: Exports trace data into structured `.npz` files with JSON metadata containing ISO timestamps and instrument settings.
- **CLI Workflow & Prompts**:
  - **Measurement Mode**: Select `1` for Single trace or `2` for Averaged trace.
  - **VISA Resource Selection**: Interactively picks connected instrument address from PyVISA resource manager.
  - **Instrument Parameters**: Prompts for start/stop frequency, RBW, detector mode (`POS`, `NEG`, `SAMP`, `AVER`), preamp toggle (`y/n`), attenuation (dB), trace count (`n_avg`), and averaging mode (`power` vs `dbm`).
  - **Data Designation**: Prompts for base filename, measurement condition (`hot` or `cold`), and file overwrite flag.

### 3. `utils.py`
Core utility module supporting instrument interaction and data serialization.
- `SpectrumAnalyzer`: Class wrapper for PyVISA SCPI communication, trace query auto-detection, and synchronization.
- **Power Conversions**: `dbm_to_mw` and `mw_to_dbm` conversion utilities for linear power averaging.
- **File Management**: `save_npz` handles file creation and metadata embedding.

---

---

## Noise Figure Plots & Data

Raw measurement data files (`.npz`) and plots are organized into:
- [**Modified LNA Data Directory (`data/modified/`)**](data/modified/)
- [**Unmodified LNA Data Directory (`data/unmodified/`)**](data/unmodified/)

{% assign files_sorted = site.static_files | sort: "path" %}

### Modified LNA Plots & Data ([browse folder](data/modified/))

<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px;">
{% for file in files_sorted %}
  {% if file.path contains "/LNA/noise_figure/plots/modified/" and file.extname == ".png" %}
    {% assign lna_id = file.basename | remove: "_nf" %}
    {% assign cold_path = "/LNA/noise_figure/data/modified/" | append: lna_id | append: "_cold_.npz" %}
    {% assign hot_path = "/LNA/noise_figure/data/modified/" | append: lna_id | append: "_hot_.npz" %}
    <div class="lna-card" style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
      <h4 style="margin: 0;">{{ file.basename }}</h4>
      <div style="aspect-ratio: 1.6; overflow: hidden; border-radius: 4px; border: 1px solid #eee;">
        <a href="{{ file.path | relative_url }}" target="_blank">
          <img src="{{ file.path | relative_url }}" alt="{{ file.basename }} Plot" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
        </a>
      </div>
      <div style="margin-top: auto; display: flex; gap: 6px; font-size: 0.85em; flex-wrap: wrap;">
        <a href="{{ file.path | relative_url }}" target="_blank" style="flex: 1; text-align: center; border: 1px solid #ccc; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: inherit; background-color: #fafafa;">View Plot</a>
        <a href="{{ cold_path | relative_url }}" download style="border: 1px solid #0366d6; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: #0366d6; background-color: #f0f7ff;">Cold NPZ</a>
        <a href="{{ hot_path | relative_url }}" download style="border: 1px solid #0366d6; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: #0366d6; background-color: #f0f7ff;">Hot NPZ</a>
      </div>
    </div>
  {% endif %}
{% endfor %}
</div>

### Unmodified LNA Plots & Data ([browse folder](data/unmodified/))

<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px;">
{% for file in files_sorted %}
  {% if file.path contains "/LNA/noise_figure/plots/unmodified/" and file.extname == ".png" %}
    {% assign lna_id = file.basename | remove: "_nf" %}
    {% assign cold_path = "/LNA/noise_figure/data/unmodified/" | append: lna_id | append: "_cold_.npz" %}
    {% assign hot_path = "/LNA/noise_figure/data/unmodified/" | append: lna_id | append: "_hot_.npz" %}
    <div class="lna-card" style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
      <h4 style="margin: 0;">{{ file.basename }}</h4>
      <div style="aspect-ratio: 1.6; overflow: hidden; border-radius: 4px; border: 1px solid #eee;">
        <a href="{{ file.path | relative_url }}" target="_blank">
          <img src="{{ file.path | relative_url }}" alt="{{ file.basename }} Plot" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
        </a>
      </div>
      <div style="margin-top: auto; display: flex; gap: 6px; font-size: 0.85em; flex-wrap: wrap;">
        <a href="{{ file.path | relative_url }}" target="_blank" style="flex: 1; text-align: center; border: 1px solid #ccc; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: inherit; background-color: #fafafa;">View Plot</a>
        <a href="{{ cold_path | relative_url }}" download style="border: 1px solid #0366d6; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: #0366d6; background-color: #f0f7ff;">Cold NPZ</a>
        <a href="{{ hot_path | relative_url }}" download style="border: 1px solid #0366d6; padding: 6px 8px; border-radius: 4px; text-decoration: none; color: #0366d6; background-color: #f0f7ff;">Hot NPZ</a>
      </div>
    </div>
  {% endif %}
{% endfor %}
</div>
