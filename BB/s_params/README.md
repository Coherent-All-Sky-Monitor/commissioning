# Backboard S-Parameter Measurements

Full 2-port S-parameter measurements of the CASM backboards (part numbers `BAC#####P1` / `BAC#####P2`), taken with the shared LibreVNA tool in [`tools/vna`](../../tools/vna/README.md):

```bash
./bac_sparams.sh   # from the repo root
```

- **[Backboard Plot & Touchstone Data Viewer](../data_viewer.md)**
- **[Backboard Diagnostic Log](../diagnostics.md)**

## Contents of the directory
- `touchstone/`: `.s2p` Touchstone files, one per part number.
- `plots/`: Magnitude/phase and Smith Chart plots, one per part number.
- [`bac_diagnostic_log.csv`](./bac_diagnostic_log.csv): Current draw and S-parameters at 444 MHz for every board, with the calibration instance and machine used.
