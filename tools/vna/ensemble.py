#!/usr/bin/env python3
"""
S-Parameter Ensemble Statistics
===============================
Summarises every measured board of a device type, per polarization, into the
JSON the data viewer pages plot: min / 5th percentile / median / 95th
percentile / max of |S11|, |S21|, |S12|, |S22| (dB) at each frequency.

Bad boards are left out, judged from the diagnostic log: current draw of 0 mA
(dead board) or S21 at DIAGNOSTIC_FREQ more than BAD_S21_SIGMA robust sigma
from the median of the log.

Writes <data_dir>/ensemble_P<n>.json next to touchstone/ and plots/. Output
depends only on the data (no timestamps), so re-running on unchanged data
gives identical files; the pre-commit hook and the GitHub Action rely on that.

Usage:
    python ensemble.py               # all devices
    python ensemble.py --device lna
"""

import argparse
import csv
import glob
import json
import os
import re

import numpy as np
import skrf as rf

from sparams import DEVICES, DIAGNOSTIC_FREQ, HIGHLIGHT_FREQ_RANGE, REPO_ROOT

# Common grid every board is interpolated onto: 1-1000 MHz, 1001 points
FREQ_GRID_HZ = np.linspace(1e6, 1e9, 1001)
BAD_S21_SIGMA = 6.0
PARAMS = {"S11": (0, 0), "S21": (1, 0), "S12": (0, 1), "S22": (1, 1)}
DECIMALS = 2   # dB; keeps the files small and the output stable


def robust_stats(values):
    """Median and robust sigma (1.4826 * median absolute deviation)."""
    values = np.asarray(values, dtype=float)
    median = np.median(values)
    return median, 1.4826 * np.median(np.abs(values - median))


def find_bad_boards(log_path):
    """
    {part_number: reason} for boards in the diagnostic log that should be left
    out of the ensemble: no current draw, or S21 far from the other boards.
    """
    with open(log_path, newline="") as f:
        rows = {r["part_number"]: r for r in csv.DictReader(f)}  # last row wins
    powered = [r for r in rows.values() if float(r["current_draw_mA"]) != 0]
    s21_median, s21_sigma = robust_stats([float(r["S21_dB"]) for r in powered])

    bad = {}
    for part, r in rows.items():
        s21 = float(r["S21_dB"])
        if float(r["current_draw_mA"]) == 0:
            bad[part] = "no current draw (0 mA)"
        elif abs(s21 - s21_median) > BAD_S21_SIGMA * s21_sigma:
            bad[part] = (f"S21 {s21:.2f} dB at {DIAGNOSTIC_FREQ/1e6:.0f} MHz "
                         f"(ensemble {s21_median:.2f} ± {s21_sigma:.2f} dB)")
    return bad


def load_magnitudes_db(path):
    """|S| in dB of each parameter on FREQ_GRID_HZ; NaN outside the board's sweep."""
    net = rf.Network(path)
    mags = {}
    for param, (i, j) in PARAMS.items():
        mag_db = 20 * np.log10(np.abs(net.s[:, i, j]) + 1e-12)
        mags[param] = np.interp(FREQ_GRID_HZ, net.f, mag_db, left=np.nan, right=np.nan)
    return mags


def summarise(paths):
    """Per-frequency statistics across boards, NaN-aware, rounded for JSON."""
    per_board = [load_magnitudes_db(p) for p in paths]
    out = {}
    for param in PARAMS:
        stack = np.array([b[param] for b in per_board])
        with np.errstate(all="ignore"):   # all-NaN columns stay NaN
            stats = {
                "min": np.nanmin(stack, axis=0),
                "p5": np.nanpercentile(stack, 5, axis=0),
                "median": np.nanmedian(stack, axis=0),
                "p95": np.nanpercentile(stack, 95, axis=0),
                "max": np.nanmax(stack, axis=0),
            }
        out[param] = {k: to_json_list(v) for k, v in stats.items()}
    return out


def to_json_list(values):
    """Rounded floats, with NaN as null."""
    return [None if np.isnan(v) else round(float(v), DECIMALS) for v in values]


def latest_measurement(log_path, parts):
    """Newest timestamp in the diagnostic log among the boards used."""
    with open(log_path, newline="") as f:
        stamps = [r["timestamp"] for r in csv.DictReader(f) if r["part_number"] in parts]
    return max(stamps, default=None)


def build_device(key):
    device = DEVICES[key]
    data_dir = os.path.join(REPO_ROOT, device["data_dir"])
    log_path = os.path.join(data_dir, device["log_file"])
    bad = find_bad_boards(log_path)

    # Group touchstones by polarization, e.g. LNA00206P1.s2p -> P1
    pattern = re.compile(rf"^{device['prefix']}\d{{5}}(P\d)$")
    groups = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "touchstone", "*.s2p"))):
        part = os.path.splitext(os.path.basename(path))[0]
        match = pattern.match(part)
        if match:
            groups.setdefault(match.group(1), []).append((part, path))

    written = []
    for pol, boards in sorted(groups.items()):
        used = [(part, path) for part, path in boards if part not in bad]
        excluded = [{"part_number": part, "reason": bad[part]} for part, _ in boards if part in bad]
        data = {
            "device": device["label"],
            "polarization": pol,
            "n_boards": len(used),
            "excluded": excluded,
            "latest_measurement": latest_measurement(log_path, {part for part, _ in used}),
            "band_mhz": [HIGHLIGHT_FREQ_RANGE[0] / 1e6, HIGHLIGHT_FREQ_RANGE[1] / 1e6],
            "freq_mhz": to_json_list(FREQ_GRID_HZ / 1e6),
            **summarise([path for _, path in used]),
        }
        out_path = os.path.join(data_dir, f"ensemble_{pol}.json")
        with open(out_path, "w") as f:
            json.dump(data, f, separators=(",", ":"))
            f.write("\n")
        written.append(out_path)
        print(f"{device['label']} {pol}: {len(used)} boards, {len(excluded)} excluded "
              f"-> {os.path.relpath(out_path, REPO_ROOT)}")
        for e in excluded:
            print(f"    excluded {e['part_number']}: {e['reason']}")

    # Drop files for polarizations that no longer have any touchstones
    for stale in glob.glob(os.path.join(data_dir, "ensemble_P*.json")):
        if stale not in written:
            os.remove(stale)
            print(f"removed {os.path.relpath(stale, REPO_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Build S-parameter ensemble JSON for the data viewer.")
    parser.add_argument("--device", choices=sorted(DEVICES), help="Only this device (default: all)")
    args = parser.parse_args()
    for key in [args.device] if args.device else sorted(DEVICES):
        build_device(key)


if __name__ == "__main__":
    main()
