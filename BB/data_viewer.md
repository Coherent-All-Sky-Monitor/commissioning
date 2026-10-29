---
layout: default
title: Backboard S-Parameter Measurements
permalink: /BB/bac_data
---

Below is a complete record of the backboard characterization sweeps. Click on any plot image to view it full size, or click **Touchstone (.s2p)** to download the corresponding data file.

* **Diagnostic Logs:** [Backboard Diagnostic Log](./diagnostics.md)

---

## Ensemble

Every board's sweep combined, one plot per polarization: median (solid), 5–95% range (shaded) and min/max (dotted). Bad boards (no current draw, or S21 far from the other boards) are left out.

{% include sparam_ensemble.html data_dir="/BB/s_params/" %}

---

## Individual Boards

{% include sparam_viewer.html plots_dir="/BB/s_params/plots/" example_id="BAC00018" %}
