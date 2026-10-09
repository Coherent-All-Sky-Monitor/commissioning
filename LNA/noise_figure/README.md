# LNA Noise Figure Measurements

Raw measurement data, generated plots and results for LNA noise figures, measured with the Y-factor method (room-temperature and liquid-nitrogen loads). The scripts live in [`tools/noise_figure`](../../tools/noise_figure/README.md); run them from the repo root:

```bash
./lna_nf_measure.sh                  # acquire a hot or cold trace from the spectrum analyzer
./lna_nf.sh -b lna173 --save-plot    # analyze one measurement
./lna_nf.sh --all                    # re-analyze everything and refresh the log
```

## Contents of the directory

- [**`data/modified/`**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/modified): Raw NPZ dataset sweeps (`_hot_.npz`, `_cold_.npz`) for modified LNAs.
- [**`data/unmodified/`**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/unmodified): Raw NPZ dataset sweeps (`_hot_.npz`, `_cold_.npz`) for unmodified LNAs.
- [**`plots/modified/`**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/plots/modified): Generated Noise Figure plots for modified LNAs.
- [**`plots/unmodified/`**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/plots/unmodified): Generated Noise Figure plots for unmodified LNAs.
- [**`nf_log.csv`**](./nf_log.csv): In-band (390–483 MHz) noise figure, noise temperature and gain for every analyzed LNA.

---

## Noise Figure Plots & Data

Raw measurement data files (`.npz`) and plots are organized into:
- [**Modified LNA Data Directory (`data/modified/`)**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/modified)
- [**Unmodified LNA Data Directory (`data/unmodified/`)**](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/unmodified)

### Modified LNA Plots & Data ([browse folder](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/modified))

{% include nf_gallery.html plots_dir="/LNA/noise_figure/plots/modified/" %}

### Unmodified LNA Plots & Data ([browse folder](https://github.com/Coherent-All-Sky-Monitor/commissioning/tree/main/LNA/noise_figure/data/unmodified))

{% include nf_gallery.html plots_dir="/LNA/noise_figure/plots/unmodified/" %}
