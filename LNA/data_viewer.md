---
layout: default
title: LNA S-Parameter Measurements
permalink: /LNA/lna_data
---

Below is a complete record of the Low Noise Amplifier (LNA) characterization sweeps. Click on any plot image to view it full size, or click **Download Touchstone** to fetch the corresponding `.s2p` data file.

* **Diagnostic Logs:** [LNA Diagnostic Log](./lna_diagnostics)

---

<div style="margin: 25px 0 15px 0; display: flex; gap: 15px; align-items: center; flex-wrap: wrap;">
  <div style="position: relative; flex: 1; max-width: 350px;">
    <input type="text" id="search-plots" placeholder="Search by LNA ID (e.g. LNA00203)..." style="padding: 10px 14px; width: 100%; border: 1px solid rgba(150, 150, 150, 0.3); border-radius: 8px; font-size: 14px; background: rgba(150, 150, 150, 0.05); color: inherit; outline: none; transition: border-color 0.2s, box-shadow 0.2s;" onfocus="this.style.borderColor='#0366d6'; this.style.boxShadow='0 0 0 3px rgba(3, 102, 214, 0.15)'" onblur="this.style.borderColor='rgba(150, 150, 150, 0.3)'; this.style.boxShadow='none'">
  </div>
  <span id="plots-count" style="font-size: 0.9em; opacity: 0.7; font-weight: 500;">Loading plots...</span>
</div>

<div id="no-results" style="display: none; padding: 40px 20px; text-align: center; color: #666; border: 1px dashed rgba(150, 150, 150, 0.3); border-radius: 8px; margin-top: 20px; font-size: 1.1em;">
  No matching LNA plots found.
</div>

{% assign files_sorted = site.static_files | sort: "path" %}

<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px;">
{% for file in files_sorted %}
  {% if file.path contains "/LNA/s_params/plots/" and file.extname == ".png" %}
    {% assign s2p_path = file.path | replace: '/plots/', '/touchstone/' | replace: '.png', '.s2p' %}
    <div class="lna-card" data-id="{{ file.basename | downcase }}" style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: rgba(250, 250, 250, 0.05); display: flex; flex-direction: column; gap: 10px;">
      <h3 style="margin-top: 0; margin-bottom: 5px;">{{ file.basename }}</h3>
      <div style="font-size: 0.85em; color: #666; margin-bottom: 5px;">
        <strong>Polarization:</strong> {% if file.basename contains "P1" %}Polarization 1{% else %}Polarization 2{% endif %}
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

<script>
  (function() {
    const cards = document.querySelectorAll('.lna-card');
    const searchInput = document.getElementById('search-plots');
    const countSpan = document.getElementById('plots-count');
    const noResultsDiv = document.getElementById('no-results');

    function updateCount(visibleCount) {
      if (countSpan) {
        countSpan.textContent = `Showing ${visibleCount} of ${cards.length} plots`;
      }
    }

    // Initialize count
    updateCount(cards.length);

    if (searchInput) {
      searchInput.addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase().trim();
        let visibleCount = 0;

        cards.forEach(card => {
          const id = card.getAttribute('data-id') || '';
          if (id.includes(query)) {
            card.style.display = 'flex';
            visibleCount++;
          } else {
            card.style.display = 'none';
          }
        });

        updateCount(visibleCount);

        if (noResultsDiv) {
          noResultsDiv.style.display = visibleCount === 0 ? 'block' : 'none';
        }
      });
    }
  })();
</script>
