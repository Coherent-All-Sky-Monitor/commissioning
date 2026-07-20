---
layout: default
title: LNA Diagnostic Log
permalink: /LNA/lna_diagnostics
---

This page displays the diagnostic logs of Low Noise Amplifiers (LNAs) recorded during characterization. 

* **Original Log File:** [lna_diagnostic_log.csv](./s_params/lna_diagnostic_log.csv)
* **S-Parameter Plots:** Go to the [S-Parameter Sweep Viewer](./lna_data)

<div style="margin: 20px 0; display: flex; gap: 10px; align-items: center;">
  <input type="text" id="search-log" placeholder="Search by LNA ID..." style="padding: 8px 12px; width: 100%; max-width: 300px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; background: inherit; color: inherit;">
  <span id="log-count" style="font-size: 0.9em; color: #666;"></span>
</div>

<div style="overflow-x: auto; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
  <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;" id="log-table">
    <thead>
      <tr style="background-color: rgba(150,150,150,0.1); border-bottom: 2px solid rgba(150,150,150,0.2);">
        <th style="padding: 12px; font-weight: 600;">LNA ID</th>
        <th style="padding: 12px; font-weight: 600;">Current (mA)</th>
        <th style="padding: 12px; font-weight: 600;">S11 (dB)</th>
        <th style="padding: 12px; font-weight: 600;">S21 (dB)</th>
        <th style="padding: 12px; font-weight: 600;">S12 (dB)</th>
        <th style="padding: 12px; font-weight: 600;">S22 (dB)</th>
        <th style="padding: 12px; font-weight: 600;">Timestamp</th>
      </tr>
    </thead>
    <tbody id="log-table-body">
      <tr>
        <td colspan="7" style="padding: 20px; text-align: center; color: #666;">Loading log data...</td>
      </tr>
    </tbody>
  </table>
</div>

<script>
  let logData = [];

  fetch('{{ "/LNA/s_params/lna_diagnostic_log.csv" | relative_url }}')
    .then(res => res.text())
    .then(text => {
      const lines = text.trim().split('\n');
      if (lines.length <= 1) {
        document.getElementById('log-table-body').innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #666;">No data found in log.</td></tr>';
        return;
      }
      
      // Parse rows
      logData = [];
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const cols = line.split(',');
        if (cols.length >= 7) {
          logData.push({
            id: cols[0],
            current: cols[1],
            s11: cols[2],
            s21: cols[3],
            s12: cols[4],
            s22: cols[5],
            timestamp: cols[6]
          });
        }
      }
      
      // Reverse order (newest first)
      logData.reverse();
      renderTable(logData);
    })
    .catch(err => {
      document.getElementById('log-table-body').innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: red;">Error loading CSV file.</td></tr>';
      console.error(err);
    });

  function renderTable(data) {
    const tbody = document.getElementById('log-table-body');
    const countSpan = document.getElementById('log-count');
    
    countSpan.textContent = `(${data.length} records)`;
    
    if (data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center; color: #666;">No matching records found.</td></tr>';
      return;
    }
    
    let html = '';
    data.forEach(row => {
      html += `<tr style="border-bottom: 1px solid rgba(150,150,150,0.15);">
        <td style="padding: 10px 12px; font-weight: 500;">${row.id}</td>
        <td style="padding: 10px 12px;">${row.current}</td>
        <td style="padding: 10px 12px;">${row.s11}</td>
        <td style="padding: 10px 12px; font-weight: 500;">${row.s21}</td>
        <td style="padding: 10px 12px;">${row.s12}</td>
        <td style="padding: 10px 12px;">${row.s22}</td>
        <td style="padding: 10px 12px; font-size: 0.9em; opacity: 0.8;">${row.timestamp.replace('T', ' ')}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  }

  document.getElementById('search-log').oninput = function(e) {
    const query = e.target.value.toLowerCase().trim();
    const filtered = logData.filter(row => 
      row.id.toLowerCase().includes(query)
    );
    renderTable(filtered);
  };
</script>
