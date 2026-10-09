# Backboard Noise Figure Measurements

Raw measurement data, generated plots and results for backboard noise figures (part numbers `BAC#####P1` / `BAC#####P2`), measured with the Y-factor method using a calibrated noise source and its ENR table. The scripts live in [`tools/noise_figure`](../../tools/noise_figure/README.md); run them from the repo root:

```bash
./bac_nf_measure.sh                       # acquire a source-on or source-off trace
./bac_nf.sh -b BAC00018P1 --save-plot     # analyze one measurement
./bac_nf.sh --all                         # re-analyze everything and refresh the log
```

## Measurement procedure

1. **Analyzer calibration:** connect the noise source straight to the spectrum analyzer and run `./bac_nf_measure.sh`, choosing *Analyzer calibration*. Take one trace with the source **on** and one with it **off**. This removes the analyzer's own noise from every measurement saved in the same subfolder.
2. **Backboard:** connect noise source → backboard → analyzer, choose *Backboard*, enter the backboard number and polarization, and take a source-on and a source-off trace.
3. **Analyze:** `./bac_nf.sh -b BAC#####P# --save-plot`.

The noise source's ENR table is [`tools/noise_figure/enr/ebay_5p5dB.csv`](../../tools/noise_figure/enr/ebay_5p5dB.csv).

## Contents of the directory

- `data/<subfolder>/`: Raw NPZ traces (`_hot_.npz` = source on, `_cold_.npz` = source off) and the analyzer calibration (`cal_hot_.npz`, `cal_cold_.npz`).
- `plots/<subfolder>/`: Generated noise figure plots.
- [**`nf_log.csv`**](./nf_log.csv): In-band (390–483 MHz) noise figure, noise temperature and gain for every analyzed backboard.

---

## Noise Figure Plots & Data

{% include nf_gallery.html plots_dir="/BB/noise_figure/plots/" %}
