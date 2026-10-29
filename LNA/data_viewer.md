---
layout: default
title: LNA S-Parameter Measurements
permalink: /LNA/lna_data
---

Below is a complete record of the Low Noise Amplifier (LNA) characterization sweeps. Click on any plot image to view it full size, or click **Download Touchstone** to fetch the corresponding `.s2p` data file.

* **Diagnostic Logs:** [LNA Diagnostic Log](./diagnostics.md)

---

## Ensemble

Every board's sweep combined, one plot per polarization: median (solid), 5–95% range (shaded) and min/max (dotted). Bad boards (no current draw, or S21 far from the other boards) are left out.

{% include sparam_ensemble.html data_dir="/LNA/s_params/" %}

---

## Individual Boards

{% include sparam_viewer.html plots_dir="/LNA/s_params/plots/" example_id="LNA00203" %}
