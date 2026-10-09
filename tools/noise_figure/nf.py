"""
Y-Factor Noise Figure Analysis
==============================
Computes receiver noise temperature, noise figure and gain from a pair of
hot/cold spectrum-analyzer traces (<base>_hot_.npz / <base>_cold_.npz)
saved by spectrum_analyzer.py into a device's noise-figure workspace.

Two ways of setting the hot/cold reference temperatures (per device):
    "loads": physical hot and cold loads at known temperatures (Th, Tc)
    "enr":   a calibrated noise source; hot = source on with
             Th(f) = T0 * (10^(ENR(f)/10) + 1), cold = source off at room temperature

Usage:
    python nf.py --device lna -b lna173 --save-plot
    python nf.py --device bac -b BAC00018P1 --save-plot
    python nf.py --device lna --all
"""

import csv
import datetime
import json
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

K_BOLTZ = 1.380649e-23  # J/K
T0_REF = 290.0          # Standard IEEE reference temperature for Noise Figure (K)

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parents[1]

# ─── Device Profiles ───────────────────────────────────────────────────────
# workspace is relative to the repo root and holds data/, plots/ and nf_log.csv.
# method "loads": th_k / tc_k are the default hot/cold load physical temperatures (K).
# method "enr":   enr_table (relative to this folder) gives the noise source ENR;
#                 tc_k is the room temperature of the source when off.
# A "load_temp_k" recorded in a trace's metadata takes precedence over th_k / tc_k.
# part_prefix: if set, acquisition builds <prefix><5 digits>P<polarization> names.

DEVICES = {
    "lna": {
        "label": "LNA",
        "workspace": "LNA/noise_figure",
        "method": "loads",
        "th_k": 296.85,   # room-temperature load
        "tc_k": 77.0,     # load in liquid nitrogen
        "part_prefix": None,
    },
    "bac": {
        "label": "Backboard",
        "workspace": "BB/noise_figure",
        "method": "enr",
        "enr_table": "enr/ebay_5p5dB.csv",
        "tc_k": 296.85,   # noise source off, at room temperature
        "part_prefix": "BAC",
    },
}

# Base name used for the analyzer-only calibration pair (noise source straight
# into the spectrum analyzer); stored next to the measurements it applies to.
CAL_BASE = "cal"

LOG_FIELDS = [
    "base", "group",
    "mean_nf_db", "std_nf_db", "median_nf_db",
    "mean_te_k", "std_te_k", "median_te_k",
    "mean_gain_db", "std_gain_db",
    "th_k", "tc_k", "rbw_hz", "mode",
    "hot_timestamp", "cold_timestamp", "processed",
    "enr_table",
]

def smooth(x, w=11):
    x = np.asarray(x, float)
    y = x.copy()
    ok = np.isfinite(x)
    if np.any(ok):
        y[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), x[ok])
    else:
        return np.full_like(x, np.nan)
    k = np.ones(w)/w
    return np.convolve(y, k, mode="same")


def prompt_float(prompt, default):
    s = input(f"{prompt} [default {default}]: ").strip()
    if not s:
        return float(default)
    return float(s)


def prompt_yes_no(prompt, default_no=True):
    s = input(prompt).strip().lower()
    if not s:
        return not default_no
    return s in ("y", "yes", "1", "true")


def dbm_to_w(dbm):
    dbm = np.asarray(dbm, dtype=np.float64)
    return 10.0 ** ((dbm - 30.0) / 10.0)


def _npz_get_first_existing(npz, keys):
    for k in keys:
        if k in npz.files:
            return k, npz[k]
    return None, None


def load_trace_npz(path: Path):
    npz = np.load(path, allow_pickle=True)

    _, freq = _npz_get_first_existing(npz, ["freq_hz", "freq"])
    if freq is None:
        raise ValueError(f"{path}: missing freq_hz/freq")
    freq = np.array(freq, dtype=np.float64)

    _, tr = _npz_get_first_existing(npz, ["trace_dbm", "trace", "data"])
    if tr is None:
        raise ValueError(f"{path}: missing trace_dbm/trace/data")
    tr = np.array(tr, dtype=np.float64)

    meta = {}
    if "metadata_json" in npz.files:
        mj = npz["metadata_json"]
        if isinstance(mj, np.ndarray):
            mj = mj.item()
        if isinstance(mj, (bytes, bytearray)):
            mj = mj.decode("utf-8", errors="replace")
        try:
            meta = json.loads(mj) if mj else {}
        except json.JSONDecodeError:
            meta = {"_metadata_json_raw": mj}

    return freq, tr, meta


def rbw_from_meta(meta):
    try:
        rbw = meta.get("rbw_hz", None)
        if rbw is None:
            rbw = meta.get("instrument_readback", {}).get("rbw_hz", None)
        if rbw is None:
            return None
        if isinstance(rbw, str):
            rbw = rbw.strip()
            if rbw == "":
                return None
            return float(rbw)
        return float(rbw)
    except Exception:
        return None


def find_measurement_folder(base: str, data_dir: Path):
    """Return the folder under data_dir holding <base>_hot_.npz (any subfolder depth)."""
    matches = sorted(p.parent for p in data_dir.rglob(f"{base}_hot_.npz"))
    if len(matches) > 1:
        raise SystemExit(f"'{base}' found in several folders: " + ", ".join(str(m) for m in matches))
    return matches[0] if matches else None


def list_bases(data_dir: Path):
    """All measurement base names under data_dir that have both hot and cold traces."""
    bases = []
    for hot in sorted(data_dir.rglob("*_hot_.npz")):
        base = hot.name[:-len("_hot_.npz")]
        if base != CAL_BASE and hot.with_name(f"{base}_cold_.npz").exists():
            bases.append(base)
    return bases


def find_measurement_files(base: str, folder: Path):
    return folder / f"{base}_hot_.npz", folder / f"{base}_cold_.npz"


def load_enr_table(path: Path):
    """
    Read a noise-source ENR table: CSV with freq_mhz,enr_db columns.
    Lines starting with '#' are comments. Returns (freq_hz, enr_db), sorted.
    """
    text = path.read_text()
    rows = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(rows)
    pts = sorted((float(r["freq_mhz"]) * 1e6, float(r["enr_db"])) for r in reader)
    if not pts:
        raise ValueError(f"{path}: no ENR points")
    if "PLACEHOLDER" in text:
        print(f"WARNING: {path.name} is a placeholder ENR table; results are only nominal.")
    freq_hz, enr_db = (np.array(c) for c in zip(*pts))
    return freq_hz, enr_db


def hot_temp_from_enr(freq_hz, enr_freq_hz, enr_db):
    """Noise-source-on temperature Th(f) = T0 * (ENR_lin + 1), ENR interpolated in dB."""
    if freq_hz[0] < enr_freq_hz[0] or freq_hz[-1] > enr_freq_hz[-1]:
        print(f"WARNING: sweep {freq_hz[0]/1e6:.0f}-{freq_hz[-1]/1e6:.0f} MHz extends past the ENR table "
              f"({enr_freq_hz[0]/1e6:.0f}-{enr_freq_hz[-1]/1e6:.0f} MHz); edge ENR values are held.")
    enr = np.interp(freq_hz, enr_freq_hz, enr_db)
    return T0_REF * (10.0 ** (enr / 10.0) + 1.0)


def load_temp_from_meta(meta):
    """Physical load temperature (K) recorded at acquisition time, if any."""
    try:
        t = float(meta.get("load_temp_k"))
        return t if np.isfinite(t) else None
    except (TypeError, ValueError):
        return None


def upsert_log(log_path: Path, row: dict):
    """Write row to the results log, replacing any previous row for the same base."""
    rows = []
    if log_path.exists():
        with open(log_path, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["base"] != row["base"]]
    rows.append(row)
    rows.sort(key=lambda r: (r["group"], r["base"]))
    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_cal_files(folder: Path):
    candidates = [
        (folder / "cal_hot.npz",  folder / "cal_cold.npz"),
        (folder / "cal_hot_.npz", folder / "cal_cold_.npz"),
    ]
    for ch, cc in candidates:
        if ch.exists() and cc.exists():
            return ch, cc
    return None, None


def nanmed(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.nanmedian(x)) if np.any(np.isfinite(x)) else float("nan")

def nanmean(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.nanmean(x)) if np.any(np.isfinite(x)) else float("nan")

def nanstd(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.nanstd(x)) if np.any(np.isfinite(x)) else float("nan")

def nanmax(x):
    x = np.asarray(x, dtype=np.float64)
    return float(np.nanmax(x)) if np.any(np.isfinite(x)) else float("nan")


def compute_yfactor_tsys_gain(hot_dbm, cold_dbm, Th, Tc, rbw_hz):
    hot_dbm = np.asarray(hot_dbm, dtype=np.float64)
    cold_dbm = np.asarray(cold_dbm, dtype=np.float64)

    Ph = dbm_to_w(hot_dbm)
    Pc = dbm_to_w(cold_dbm)
    Pc = np.maximum(Pc, 1e-30)

    Y = Ph / Pc
    denom = (Y - 1.0)
    good = np.isfinite(Y) & np.isfinite(denom) & (denom > 0)

    # Th / Tc may be scalars or per-frequency arrays (ENR noise source)
    Th = np.broadcast_to(np.asarray(Th, dtype=np.float64), Y.shape)
    Tc = np.broadcast_to(np.asarray(Tc, dtype=np.float64), Y.shape)

    Te = np.full_like(Y, np.nan, dtype=np.float64)
    Te[good] = (Th[good] - Y[good] * Tc[good]) / denom[good]

    B = float(rbw_hz)
    denom_g = K_BOLTZ * B * (Tc + Te)
    good_g = good & np.isfinite(denom_g) & (denom_g > 0)

    G = np.full_like(Y, np.nan, dtype=np.float64)
    G[good_g] = Pc[good_g] / denom_g[good_g]

    G_db = np.full_like(Y, np.nan, dtype=np.float64)
    G_db[good_g] = 10.0 * np.log10(G[good_g])

    return Y, Te, G, G_db


def shade_band(ax, f0_mhz, f1_mhz):
    ax.axvspan(f0_mhz, f1_mhz, color="gold", alpha=0.18)


def scatter_inband(ax, freq_mhz, y, inband, label_in="in band", label_oob="out of band"):
    oob = np.isfinite(y) & (~inband)
    ax.scatter(freq_mhz[oob], y[oob], s=8, alpha=0.25, color="tab:blue", label=label_oob)

    ib = np.isfinite(y) & inband
    ax.scatter(freq_mhz[ib], y[ib], s=10, alpha=0.9, color="tab:red", label=label_in)


def analyze(base, folder: Path, device, th_k=None, tc_k=None, smooth_flag=True,
            interactive=False, save_plot=False, show=True, enr_table=None):
    """
    Run the Y-factor analysis for one hot/cold pair in `folder`.

    th_k / tc_k override the load temperatures; otherwise the temperature
    recorded in each trace's metadata is used, then the device default.
    For "enr" devices Th comes from the ENR table (enr_table overrides the
    device's table) and th_k is ignored.
    Returns the row written to the results log, or None if files are missing.
    """
    hot_path, cold_path = find_measurement_files(base, folder)
    if not hot_path.exists() or not cold_path.exists():
        print(f"Missing required files. Need both:\n  {hot_path}\n  {cold_path}")
        return None

    freq_hz, hot_dbm, hot_meta = load_trace_npz(hot_path)
    freq2, cold_dbm, cold_meta = load_trace_npz(cold_path)
    if freq_hz.shape != freq2.shape or not np.allclose(freq_hz, freq2):
        print("Hot/cold frequency axes do not match. Exiting.")
        return None

    print(f"Loaded successfully: {hot_path.relative_to(REPO_ROOT)}")
    print(f"Loaded successfully: {cold_path.relative_to(REPO_ROOT)}")

    Tc = tc_k if tc_k is not None else (load_temp_from_meta(cold_meta) or device["tc_k"])
    enr_path = None
    if device["method"] == "enr":
        enr_path = Path(enr_table) if enr_table else TOOLS_DIR / device["enr_table"]
        Th = hot_temp_from_enr(freq_hz, *load_enr_table(enr_path))
        print(f"Noise source: ENR table {enr_path.name}, Th = {Th.min():.0f}-{Th.max():.0f} K; source off Tc = {Tc} K")
    else:
        Th = th_k if th_k is not None else (load_temp_from_meta(hot_meta) or device["th_k"])
        print(f"Load temperatures: Th = {Th} K, Tc = {Tc} K")

    rbw = rbw_from_meta(hot_meta or {}) or rbw_from_meta(cold_meta or {})
    if rbw is None or not np.isfinite(rbw) or rbw <= 0:
        if interactive:
            rbw = prompt_float("RBW/Noise bandwidth B (Hz) for gain calc", 100e3)
        else:
            rbw = 100e3
            print(f"Metadata readback null context error. Defaulting bandwidth target down to: {rbw} Hz")

    _, Te_tot, G_tot, G_tot_db = compute_yfactor_tsys_gain(hot_dbm, cold_dbm, Th, Tc, rbw)

    cal_hot_path, cal_cold_path = find_cal_files(folder)
    using = "TOTAL"
    Te_plot = Te_tot
    Gdb_plot = G_tot_db

    if cal_hot_path is not None:
        f_ch, cal_hot_dbm, cal_hot_meta = load_trace_npz(cal_hot_path)
        f_cc, cal_cold_dbm, cal_cold_meta = load_trace_npz(cal_cold_path)

        if (f_ch.shape == freq_hz.shape and np.allclose(f_ch, freq_hz) and
            f_cc.shape == freq_hz.shape and np.allclose(f_cc, freq_hz)):

            rbw_cal = rbw_from_meta(cal_hot_meta or {}) or rbw_from_meta(cal_cold_meta or {}) or rbw
            _, Te_cal, G_cal, _G_cal_db = compute_yfactor_tsys_gain(cal_hot_dbm, cal_cold_dbm, Th, Tc, rbw_cal)

            G_dut = G_tot / G_cal
            G_dut_db = 10.0 * np.log10(G_dut)
            Te_dut = Te_tot - (Te_cal / G_dut)

            using = "DUT-only"
            Te_plot = Te_dut
            Gdb_plot = G_dut_db
            print(f"\nFound calibration baseline: {cal_hot_path.name}, {cal_cold_path.name}")
        else:
            print("\nCalibration tracking found, but frequency matrix boundaries do not match. Defaulting to TOTAL.")
    else:
        print("\nNo de-embedding path baseline pair visible. Utilizing absolute TOTAL calculations.")

    # Noise Figure Calculation Sequence (F = 1 + Te/T0)
    NF_linear = 1.0 + (Te_plot / T0_REF)
    NF_plot = np.where(NF_linear > 0, 10.0 * np.log10(np.clip(NF_linear, 1e-12, None)), np.nan)

    # Window Axis Boundary Setup Config Properties
    f0_mhz, f1_mhz = 390.0, 483.0
    freq_mhz = freq_hz / 1e6
    inband = (freq_mhz >= f0_mhz) & (freq_mhz <= f1_mhz)

    # Metric Extraction Subsystem
    med_gain_inband = nanmed(Gdb_plot[inband])
    mean_gain_inband = nanmean(Gdb_plot[inband])
    std_gain_inband = nanstd(Gdb_plot[inband])
    med_tsys_inband = nanmed(Te_plot[inband])
    mean_tsys_inband = nanmean(Te_plot[inband])
    std_tsys_inband = nanstd(Te_plot[inband])
    max_tsys_inband = nanmax(Te_plot[inband])
    med_nf_inband = nanmed(NF_plot[inband])
    mean_nf_inband = nanmean(NF_plot[inband])
    std_nf_inband = nanstd(NF_plot[inband])
    max_nf_inband = nanmax(NF_plot[inband])

    # Dynamic Limits
    gain_ymin = 0.0
    gain_ymax = med_gain_inband + 5.0 if np.isfinite(med_gain_inband) else None

    tsys_ymin = 0.0
    if np.isfinite(max_tsys_inband) or np.isfinite(med_tsys_inband):
        tsys_ymax = max(max_tsys_inband + 3.0, med_tsys_inband + 5.0)
    else:
        tsys_ymax = None

    nf_ymin = 0.0
    if np.isfinite(max_nf_inband) or np.isfinite(med_nf_inband):
        nf_ymax = max(max_nf_inband + 0.5, med_nf_inband + 1.0)
    else:
        nf_ymax = None

    print("\n=== In-band stats (390–483 MHz) ===")
    print("Using Calculations Mode: ", using)
    print(f"Median Gain in-band      : {med_gain_inband:.2f} dB")
    print(f"Mean Gain in-band        : {mean_gain_inband:.2f} dB")
    print(f"Std Dev Gain in-band     : {std_gain_inband:.2f} dB")
    print(f"Median Tsys in-band      : {med_tsys_inband:.1f} K")
    print(f"Mean Tsys in-band        : {mean_tsys_inband:.1f} K")
    print(f"Std Dev Tsys in-band     : {std_tsys_inband:.1f} K")
    print(f"Max    Tsys in-band      : {max_tsys_inband:.1f} K")
    print(f"Median Noise Figure (NF) : {med_nf_inband:.2f} dB")
    print(f"Mean Noise Figure (NF)   : {mean_nf_inband:.2f} dB")
    print(f"Std Dev Noise Figure (NF): {std_nf_inband:.2f} dB")

    gain_vector = smooth(Gdb_plot) if smooth_flag else Gdb_plot
    tsys_vector = smooth(Te_plot) if smooth_flag else Te_plot
    nf_vector   = smooth(NF_plot) if smooth_flag else NF_plot

    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    ax_tr = axs[0, 0]   # Row 1, Col 1: Traces
    ax_nf = axs[0, 1]   # Row 1, Col 2: Noise Figure
    ax_g  = axs[1, 0]   # Row 2, Col 1: Gain
    ax_t  = axs[1, 1]   # Row 2, Col 2: Tsys

    # Plot [0, 0]: Input Signal Data 
    shade_band(ax_tr, f0_mhz, f1_mhz)
    hot_label, cold_label = ("source on", "source off") if enr_path else ("hot", "cold")
    ax_tr.plot(freq_mhz, hot_dbm, label=hot_label, lw=1.2)
    ax_tr.plot(freq_mhz, cold_dbm, label=cold_label, lw=1.2)
    ax_tr.set_title(f"{base}: Input Power Profiles (RBW={rbw:.0f} Hz)")
    ax_tr.set_xlabel("Frequency (MHz)")
    ax_tr.set_ylabel("Power Amplitude (dBm)")
    ax_tr.grid(True, alpha=0.3)
    ax_tr.legend(loc="best")

    # Plot [0, 1]:  Noise Figure (NF dB)
    shade_band(ax_nf, f0_mhz, f1_mhz)
    scatter_inband(ax_nf, freq_mhz, nf_vector, inband)
    ax_nf.set_title(f"{base}: Mean In-Band NF {mean_nf_inband:.2f} +/-{std_nf_inband:.2f} dB")
    ax_nf.set_xlabel("Frequency (MHz)")
    ax_nf.set_ylabel("Noise Figure (dB)")
    ax_nf.grid(True, alpha=0.3)
    ax_nf.legend(loc="best")
    ax_nf.set_ylim(bottom=nf_ymin)
    if nf_ymax is not None:
        ax_nf.set_ylim(top=nf_ymax)

    # Plot [1, 0]: Device  Gain (dB)
    shade_band(ax_g, f0_mhz, f1_mhz)
    scatter_inband(ax_g, freq_mhz, gain_vector, inband)
    ax_g.set_title(f"{base}: Mean In-Band Gain {mean_gain_inband:.1f} +/-{std_gain_inband:.1f} dB")
    ax_g.set_xlabel("Frequency (MHz)")
    ax_g.set_ylabel("Transducer Gain (dB)")
    ax_g.grid(True, alpha=0.3)
    ax_g.legend(loc="best")
    ax_g.set_ylim(bottom=gain_ymin)
    if gain_ymax is not None:
        ax_g.set_ylim(top=gain_ymax)

    # Plot [1, 1]: Equivalent System Noise Temperature
    shade_band(ax_t, f0_mhz, f1_mhz)
    scatter_inband(ax_t, freq_mhz, tsys_vector, inband)
    ax_t.set_title(f"{base}: Mean In-Band Tsys {mean_tsys_inband:.1f} +/-{std_tsys_inband:.1f} K")
    ax_t.set_xlabel("Frequency (MHz)")
    ax_t.set_ylabel("Temperature Tsys (K)")
    ax_t.grid(True, alpha=0.3)
    ax_t.legend(loc="best")
    ax_t.set_ylim(bottom=tsys_ymin)
    if tsys_ymax is not None:
        ax_t.set_ylim(top=tsys_ymax)

    plt.tight_layout()

    # Plots mirror the data layout: data/<group>/<base>_*.npz -> plots/<group>/<base>_nf.png
    workspace = REPO_ROOT / device["workspace"]
    group = folder.relative_to(workspace / "data").as_posix()
    group = "" if group == "." else group

    should_save = save_plot or (interactive and prompt_yes_no(f"Save report graphic figure down to disk as {base}_nf.png? [y/N]: ", default_no=True))
    if should_save:
        out = workspace / "plots" / group / f"{base}_nf.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=250, bbox_inches="tight")
        print("File save output operation success path mapped directly to:\n ->", out)

    row = {
        "base": base,
        "group": group,
        "mean_nf_db": round(mean_nf_inband, 3), "std_nf_db": round(std_nf_inband, 3),
        "median_nf_db": round(med_nf_inband, 3),
        "mean_te_k": round(mean_tsys_inband, 2), "std_te_k": round(std_tsys_inband, 2),
        "median_te_k": round(med_tsys_inband, 2),
        "mean_gain_db": round(mean_gain_inband, 2), "std_gain_db": round(std_gain_inband, 2),
        # For an ENR source Th varies with frequency; log its in-band mean
        "th_k": round(float(np.mean(np.broadcast_to(Th, freq_hz.shape)[inband])), 2),
        "tc_k": Tc, "rbw_hz": rbw, "mode": using,
        "hot_timestamp": hot_meta.get("timestamp_iso", ""),
        "cold_timestamp": cold_meta.get("timestamp_iso", ""),
        "processed": datetime.datetime.now().isoformat(timespec="seconds"),
        "enr_table": enr_path.name if enr_path else "",
    }
    log_path = workspace / "nf_log.csv"
    upsert_log(log_path, row)
    print(f"Logged to: {log_path}")

    if show:
        plt.show()
    plt.close(fig)
    return row


def main():
    parser = argparse.ArgumentParser(description="Automated Y-Factor Noise Figure Calculation & Plotting Tool.")
    parser.add_argument("--device", choices=sorted(DEVICES), default="lna", help="Device workspace to read from and write to.")
    parser.add_argument("-I", "--interactive", action="store_true", help="Drop into interactive runtime input mode prompts.")
    parser.add_argument("-b", "--base", type=str, help="Measurement base name, e.g. lna173 (searched for under the workspace's data/ folder).")
    parser.add_argument("--all", action="store_true", help="Analyze every hot/cold pair in the workspace, save all plots and refresh the log.")
    parser.add_argument("--th", type=float, help="Hot load physical temperature (K). Overrides metadata and device default.")
    parser.add_argument("--tc", type=float, help="Cold load physical temperature (K). Overrides metadata and device default.")
    parser.add_argument("--enr-table", help="ENR table CSV to use instead of the device's (noise-source devices only).")
    parser.add_argument("--no-smooth", action="store_false", dest="smooth", help="Plot raw traces instead of the smoothed ones.")
    parser.add_argument("--save-plot", action="store_true", help="Save the plot to the workspace's plots/ folder.")
    parser.add_argument("--no-show", action="store_true", help="Don't open the plot window.")

    args = parser.parse_args()
    device = DEVICES[args.device]
    data_dir = REPO_ROOT / device["workspace"] / "data"

    if args.all:
        bases = list_bases(data_dir)
        print(f"Analyzing {len(bases)} measurement(s) in {data_dir}")
        for base in bases:
            print(f"\n{'=' * 60}\n{base}\n{'=' * 60}")
            analyze(base, find_measurement_folder(base, data_dir), device,
                    th_k=args.th, tc_k=args.tc, smooth_flag=args.smooth,
                    save_plot=True, show=False, enr_table=args.enr_table)
        return

    if args.interactive:
        base = input("Enter base name: ").strip()
        if not base:
            print("No base name. Exiting.")
            return
        folder = find_measurement_folder(base, data_dir)
        if folder is None:
            print(f"No {base}_hot_.npz found under {data_dir}")
            return
        hot_meta = load_trace_npz(find_measurement_files(base, folder)[0])[2]
        cold_meta = load_trace_npz(find_measurement_files(base, folder)[1])[2]
        Tc = prompt_float("Cold temperature Tc (K)", args.tc or load_temp_from_meta(cold_meta) or device["tc_k"])
        Th = None  # from the ENR table for noise-source devices
        if device["method"] == "loads":
            Th = prompt_float("Hot temperature Th (K)", args.th or load_temp_from_meta(hot_meta) or device["th_k"])
        smooth_flag = prompt_yes_no("Apply noise trace vector smoothing kernel? [Y/n]: ", default_no=False)
        analyze(base, folder, device, th_k=Th, tc_k=Tc, smooth_flag=smooth_flag, interactive=True,
                enr_table=args.enr_table)
        return

    if not args.base:
        parser.error("Missing critical argument parameter: --base / -b is mandatory when operating outside interactive mode.")
    folder = find_measurement_folder(args.base, data_dir)
    if folder is None:
        print(f"No {args.base}_hot_.npz found under {data_dir}")
        print("Available: " + ", ".join(list_bases(data_dir)))
        return
    analyze(args.base, folder, device, th_k=args.th, tc_k=args.tc, smooth_flag=args.smooth,
            save_plot=args.save_plot, show=not args.no_show, enr_table=args.enr_table)


if __name__ == "__main__":
    main()
