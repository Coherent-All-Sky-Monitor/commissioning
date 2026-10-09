# LNA S-Parameter Measurements

Full 2-port S-parameter measurements of the CASM LNAs (part numbers `LNA#####P1` / `LNA#####P2`), taken with the shared LibreVNA tool in [`tools/vna`](../../tools/vna/README.md):

```bash
./lna_sparams.sh   # from the repo root
```

- **[LNA Plot & Touchstone Data Viewer](../data_viewer.md)**
- **[LNA Diagnostic Log](../diagnostics.md)**

## Contents of the directory
- `touchstone/`: `.s2p` Touchstone files, one per part number.
- `plots/`: Magnitude/phase and Smith Chart plots, one per part number.
- [`lna_diagnostic_log.csv`](./lna_diagnostic_log.csv): Current draw and S-parameters at 444 MHz for every LNA. Rows measured after the move to `tools/vna` also record the calibration instance and machine used.
- `lna_diagnostic_log.xlsx`: Spreadsheet copy of the log.
