---
layout: default
title: LNA S-Parameter Measurements
permalink: /LNA/lna_data
---

Below is a complete record of the Low Noise Amplifier (LNA) characterization sweeps. Click on any plot image to view it full size, or click **Download Touchstone** to fetch the corresponding `.s2p` data file.

* **Diagnostic Logs:** [LNA Cumulative Diagnostic Log Table](./lna_diagnostics)

---

{% assign files_sorted = site.static_files | sort: "path" %}

<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px;">
{% for file in files_sorted %}
  {% if file.path contains "/LNA/s_params/plots/" and file.extname == ".png" %}
    {% assign s2p_path = file.path | replace: '/plots/', '/touchstone/' | replace: '.png', '.s2p' %}
    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: rgba(250, 250, 250, 0.05); display: flex; flex-direction: column; gap: 10px;">
      <h3 style="margin-top: 0; margin-bottom: 5px;">{{ file.basename }}</h3>
      <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">
        <strong>Port:</strong> {% if file.basename contains "P1" %}Port 1{% else %}Port 2{% endif %}
      </div>
      <div style="aspect-ratio: 1.6; overflow: hidden; border-radius: 4px; border: 1px solid #eee; background-color: #fcfcfc;">
        <a href="{{ file.path | relative_url }}" target="_blank">
          <img src="{{ file.path | relative_url }}" alt="{{ file.basename }} Plot" style="width: 100%; height: 100%; object-fit: cover;" loading="lazy">
        </a>
      </div>
      <div style="margin-top: auto; display: flex; gap: 10px;">
        <a href="{{ file.path | relative_url }}" target="_blank" style="flex: 1; text-align: center; font-size: 0.85em; border: 1px solid #ccc; padding: 6px 12px; border-radius: 4px; text-decoration: none; color: inherit; background-color: #fafafa;">View Full Plot</a>
        <a href="{{ s2p_path | relative_url }}" download style="flex: 1; text-align: center; font-size: 0.85em; border: 1px solid #ccc; padding: 6px 12px; border-radius: 4px; text-decoration: none; color: white; background-color: #0366d6;">Touchstone (.s2p)</a>
      </div>
    </div>
  {% endif %}
{% endfor %}
</div>
