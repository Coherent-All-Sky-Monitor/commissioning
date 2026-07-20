#!/usr/bin/env python3
"""
LNA S-Parameter Measurement Tool for LibreVNA
================================================
CLI tool for automated LNA characterization using
LibreVNA + LibreCAL via SCPI over TCP.

Prerequisites:
    - LibreVNA-GUI running with SCPI server enabled (port 19542)
    - LibreVNA hardware connected via USB
    - Python packages: rich, numpy, matplotlib, scikit-rf

Usage:
    python lna_sparams.py

Author: CASM Commissioning
"""

import csv
import datetime
import os
import re
import sys
import time
import subprocess
import atexit
import argparse

import numpy as np
import matplotlib
import matplotlib

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    import skrf as rf
    HAS_SKRF = True
except ImportError:
    HAS_SKRF = False

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

from libreVNA import libreVNA
from cal_manager import CalInstancesManager, apply_port_extension

import numpy as np
import datetime

# ─── Configurable Constants ─────────────────────────────────────────────────

HIGHLIGHT_FREQ_RANGE = (390e6, 483e6)   # Hz — shaded band on plots
DIAGNOSTIC_FREQ = 444e6                  # Hz — single-freq diagnostic point
DEFAULT_POWER = -40                      # dBm
DEFAULT_IFBW = 10000                     # Hz
DEFAULT_NUM_POINTS = 501                 # Number of sweep points
VNA_HOST = "localhost"
VNA_PORT = 19542

# Output paths (relative to this script's directory)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOUCHSTONE_DIR = os.path.join(SCRIPT_DIR, "touchstone")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")
CSV_FILE = os.path.join(SCRIPT_DIR, "lna_diagnostic_log.csv")

console = Console()

# ─── Part Number Helpers ────────────────────────────────────────────────────

PART_NUMBER_REGEX = re.compile(r'^LNA(\d{5})P([12])$')


def make_part_number(lna_num: int, polarization: int) -> str:
    """Generate part number string: LNA[00000-99999]P[1-2]."""
    return f"LNA{lna_num:05d}P{polarization}"


def validate_lna_number(value: str) -> int:
    """Validate and return a 5-digit LNA number."""
    try:
        num = int(value)
    except ValueError:
        raise ValueError("Must be a number between 0 and 99999")
    if not (0 <= num <= 99999):
        raise ValueError("Must be between 0 and 99999")
    return num


# ─── LibreVNA Controller ───────────────────────────────────────────────────

class LibreVNAController:
    """Wraps SCPI communication with the LibreVNA."""

    def __init__(self, host=VNA_HOST, port=VNA_PORT):
        self.host = host
        self.port = port
        self.vna = None
        self.start_freq = None
        self.stop_freq = None
        self.num_points = None
        self.power = None
        self.ifbw = None

    def connect(self):
        """Connect to LibreVNA-GUI SCPI server and verify hardware."""
        self.vna = libreVNA(self.host, self.port)
        idn = self.vna.query("*IDN?")
        console.print(f"  SCPI server: [cyan]{idn}[/]")

        # Ensure hardware is connected
        self.vna.cmd(":DEV:CONN")
        time.sleep(0.5)
        dev = self.vna.query(":DEV:CONN?")
        if "Not connected" in dev:
            raise ConnectionError(
                "LibreVNA hardware not connected. Check USB cable and "
                "ensure device appears in the LibreVNA-GUI."
            )
        console.print(f"  Hardware: [green]{dev}[/]")
        return dev

    def set_vna_mode(self):
        """Switch to VNA mode and set sweep type to frequency."""
        self.vna.cmd(":DEV:MODE VNA")
        time.sleep(0.3)
        self.vna.cmd(":VNA:SWEEP FREQUENCY")
        time.sleep(0.2)

    def configure_sweep(self, start_freq, stop_freq, num_points, power, ifbw):
        """Configure VNA sweep parameters."""
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.num_points = num_points
        self.power = power
        self.ifbw = ifbw

        self.vna.cmd(f":VNA:FREQuency:START {int(start_freq)}")
        self.vna.cmd(f":VNA:FREQuency:STOP {int(stop_freq)}")
        self.vna.cmd(f":VNA:ACQ:POINTS {int(num_points)}")
        self.vna.cmd(f":VNA:STIM:LVL {power}")
        self.vna.cmd(f":VNA:ACQ:IFBW {int(ifbw)}")
        self.vna.cmd(":VNA:ACQ:AVG 1")
        time.sleep(0.5)

    def load_calibration(self, cal_path):
        """Load a calibration file and configure sweep parameters to match it."""
        import json
        
        # Load calibration using the correct SCPI query syntax
        res = self.vna.query(f':VNA:CALibration:LOAD? "{cal_path}"')
        
        # Parse the JSON cal file to extract calibration sweep range
        try:
            with open(cal_path, 'r') as f:
                cal_data = json.load(f)
            points = cal_data['measurements'][0]['data']['points']
            start_freq = points[0]['frequency']
            stop_freq = points[-1]['frequency']
            num_points = len(points)
            
            # Default to -40 dBm power, and fetch IFBW or fallback to 1000.0
            power = float(DEFAULT_POWER)
            try:
                ifbw = float(self.vna.query(":VNA:ACQ:IFBW?"))
            except Exception:
                ifbw = 1000.0
                
            self.configure_sweep(start_freq, stop_freq, num_points, power, ifbw)
        except Exception as e:
            # Silent fallback if cal file parsing fails
            pass
        time.sleep(1.0)

    def save_calibration(self, cal_path):
        """Save current calibration to file."""
        self.vna.cmd(f':VNA:CAL:SAVE "{cal_path}"')
        time.sleep(1.0)

    def measure_single_sweep(self):
        """
        Trigger a single sweep and wait for completion.

        Returns:
            dict: {param: [(freq, complex), ...]} for S11, S21, S12, S22
        """
        # Trigger single sweep
        self.vna.cmd(":VNA:ACQ:SINGLE TRUE")
        time.sleep(0.5)

        # Wait for sweep completion
        timeout = 60  # seconds
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.vna.query(":VNA:ACQ:FIN?")
            if status in ("TRUE", "1"):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("Sweep did not complete within 60 seconds")

        # Small settling delay
        time.sleep(0.3)

        # Retrieve trace data for all 4 S-parameters
        results = {}
        for param in ["S11", "S21", "S12", "S22"]:
            raw = self.vna.query(f":VNA:TRAC:DATA? {param}", timeout=30)
            parsed = self.vna.parse_VNA_trace_data(raw)
            if not parsed:
                raise RuntimeError(
                    f"No data returned for {param}.\n"
                    f"  [bold red]FIX:[/] You must add the {param} trace in the LibreVNA GUI.\n"
                    f"  (Trace -> Add Trace -> Select {param}). All 4 traces (S11, S21, S12, S22) must be visible!"
                )
            results[param] = parsed

        return results

    def close(self):
        """Close connection."""
        if self.vna:
            self.vna.close()


# ─── Measurement Manager ───────────────────────────────────────────────────

class MeasurementManager:
    """Handles file I/O, CSV logging, and directory management."""

    def __init__(self):
        os.makedirs(TOUCHSTONE_DIR, exist_ok=True)
        os.makedirs(PLOTS_DIR, exist_ok=True)

    # ── Touchstone ──────────────────────────────────────────────────────

    def save_touchstone(self, results, part_number, start_freq, stop_freq):
        """
        Save full 2-port S-parameter data as a Touchstone .s2p file.

        Args:
            results: dict of {param: [(freq, complex), ...]}
            part_number: e.g. "LNA00001P1"
            start_freq, stop_freq: for frequency array generation
        """
        if not HAS_SKRF:
            console.print(
                "[yellow]⚠ scikit-rf not installed — "
                "touchstone file not saved[/]"
            )
            return None

        # Extract frequency array from S11 data
        freqs = np.array([pt[0] for pt in results["S11"]])
        n_points = len(freqs)

        # Build S-parameter matrix [n_points x 2 x 2]
        s_matrix = np.zeros((n_points, 2, 2), dtype=complex)
        s_matrix[:, 0, 0] = [pt[1] for pt in results["S11"]]
        s_matrix[:, 0, 1] = [pt[1] for pt in results["S12"]]
        s_matrix[:, 1, 0] = [pt[1] for pt in results["S21"]]
        s_matrix[:, 1, 1] = [pt[1] for pt in results["S22"]]

        # Create scikit-rf Network
        freq_obj = rf.Frequency.from_f(freqs, unit='Hz')
        network = rf.Network(
            name=part_number,
            s=s_matrix,
            frequency=freq_obj,
            z0=50,
        )

        filepath = os.path.join(TOUCHSTONE_DIR, f"{part_number}.s2p")
        network.write_touchstone(filepath)
        return filepath

    # ── Plotting ────────────────────────────────────────────────────────

    def plot_s_parameters(self, results, part_number):
        import matplotlib.gridspec as gridspec
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Increase width slightly so Smith Charts can be larger
        fig = plt.figure(figsize=(14, 8))
        fig.suptitle(
            f"S-Parameters: {part_number} | {timestamp}",
            fontsize=15, y=0.98
        )

        gs_main = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1, 1.2], wspace=0.15)
        
        # Left side: 4 rectangular plots (2x2) with zero space
        gs_left = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs_main[0], wspace=0.0, hspace=0.0)
        
        # Right side: 4 smith charts (2x2)
        gs_right = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=gs_main[1], wspace=0.1, hspace=0.1)

        params = ["S11", "S21", "S12", "S22"]
        pos_2x2 = {"S11": (0, 0), "S21": (0, 1), "S12": (1, 0), "S22": (1, 1)}

        # Build temp network for scikit-rf Smith plots
        has_skrf_local = False
        if HAS_SKRF:
            try:
                freqs = np.array([pt[0] for pt in results["S11"]])
                n_points = len(freqs)
                s_matrix = np.zeros((n_points, 2, 2), dtype=complex)
                s_matrix[:, 0, 0] = [pt[1] for pt in results["S11"]]
                s_matrix[:, 0, 1] = [pt[1] for pt in results["S12"]]
                s_matrix[:, 1, 0] = [pt[1] for pt in results["S21"]]
                s_matrix[:, 1, 1] = [pt[1] for pt in results["S22"]]
                freq_obj = rf.Frequency.from_f(freqs, unit='Hz')
                temp_ntwk = rf.Network(s=s_matrix, frequency=freq_obj, z0=50)
                has_skrf_local = True
            except Exception:
                has_skrf_local = False

        # Create rectangular axes with shared scales using subplots to auto-prune overlapping ticks
        ax_rect = {}
        axes_left = gs_left.subplots(sharex=True, sharey=True)
        ax_rect["S11"] = axes_left[0, 0]
        ax_rect["S21"] = axes_left[0, 1]
        ax_rect["S12"] = axes_left[1, 0]
        ax_rect["S22"] = axes_left[1, 1]

        ax_phase = {}
        for p in params:
            ax_phase[p] = ax_rect[p].twinx()
            if p != "S11":
                ax_phase[p].sharey(ax_phase["S11"])

        ax_smith = {}
        for p in params:
            r, c = pos_2x2[p]
            ax_smith[p] = fig.add_subplot(gs_right[r, c])

        for param in params:
            # ── Log Mag Plot ──
            ax_mag = ax_rect[param]
            freqs = np.array([pt[0] for pt in results[param]])
            complex_vals = np.array([pt[1] for pt in results[param]])
            freq_mhz = freqs / 1e6
            magnitude_db = 20 * np.log10(np.abs(complex_vals) + 1e-12)
            phase_deg = np.degrees(np.angle(complex_vals))

            # Highlight band
            hl_start = HIGHLIGHT_FREQ_RANGE[0] / 1e6
            hl_stop = HIGHLIGHT_FREQ_RANGE[1] / 1e6
            ax_mag.axvspan(
                hl_start, hl_stop,
                alpha=0.12, color='#2196F3', zorder=0,
                label=f'{hl_start:.0f}–{hl_stop:.0f} MHz'
            )

            color_mag = '#1565C0'
            ax_mag.plot(
                freq_mhz, magnitude_db,
                color=color_mag, linewidth=1.5, linestyle='-',
                label=f'|{param}| (dB)'
            )
            ax_mag.grid(True, alpha=0.3)
            
            # Inline Title
            ax_mag.text(0.05, 0.95, param, transform=ax_mag.transAxes, 
                        fontsize=13, va='top', ha='left',
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))

            ax_ph = ax_phase[param]
            color_phase = '#E65100'
            ax_ph.plot(
                freq_mhz, phase_deg,
                color=color_phase, linewidth=1.0, linestyle=':',
                alpha=0.75,
                label=f'∠{param} (°)'
            )
            
            # Legend
            lines_mag, labels_mag = ax_mag.get_legend_handles_labels()
            lines_phase, labels_phase = ax_ph.get_legend_handles_labels()
            # Only put legend on S11 to reduce clutter, since it's shared
            if param == "S11":
                ax_mag.legend(
                    lines_mag + lines_phase,
                    labels_mag + labels_phase,
                    loc='lower left', fontsize=8, framealpha=0.8
                )

            # ── Smith Chart Plot ──
            ax_sm = ax_smith[param]
            if has_skrf_local:
                m = 1 if param[1] == '2' else 0
                n = 1 if param[2] == '2' else 0
                temp_ntwk.plot_s_smith(m=m, n=n, ax=ax_sm, show_legend=False)
                
                # Top left inline title for Smith
                # For smith chart, axes limits are typically -1 to 1. 
                # transAxes (0,1) is top left of bounding box
                ax_sm.text(0.0, 1.0, param, transform=ax_sm.transAxes,
                           fontsize=13, va='top', ha='left',
                           bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))
            else:
                ax_sm.text(0.5, 0.5, "skrf missing", ha='center', va='center')
                ax_sm.axis('off')
                
        # Hardcode phase limits so they align perfectly
        for p in params:
            ax_phase[p].set_ylim(-180, 180)
            if p in ["S11", "S21"]:
                ax_phase[p].set_yticks([-90, 0, 90, 180])
            else:
                ax_phase[p].set_yticks([-180, -90, 0, 90, 180])

        # gs_left.subplots(sharex=True, sharey=True) already hides inner tick labels for X and left Y.
        # We just need to add the master labels.
        for p in ["S12", "S22"]:
            ax_rect[p].set_xlabel('Frequency (MHz)', fontsize=10)

        for p in ["S11", "S12"]:
            ax_rect[p].set_ylabel('Magnitude (dB)', color='#1565C0', fontsize=10)
            ax_rect[p].tick_params(axis='y', labelcolor='#1565C0')

        # Hide phase Y ticks on the left side
        for p in ["S11", "S12"]:
            plt.setp(ax_phase[p].get_yticklabels(), visible=False)
            
        for p in ["S21", "S22"]:
            ax_phase[p].set_ylabel('Phase (°)', color='#E65100', fontsize=10)
            ax_phase[p].tick_params(axis='y', labelcolor='#E65100')

        # Remove double tight_layout and rely on GridSpec
        filepath = os.path.join(PLOTS_DIR, f"{part_number}.png")
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return filepath

    # ── Diagnostics ─────────────────────────────────────────────────────

    def get_diagnostic_values(self, results, diag_freq=DIAGNOSTIC_FREQ):
        """
        Extract S-parameter magnitudes at the diagnostic frequency.

        Returns:
            dict: {param: magnitude_dB} for S11, S21, S12, S22
        """
        diag = {}
        for param in ["S11", "S21", "S12", "S22"]:
            freqs = np.array([pt[0] for pt in results[param]])
            complex_vals = np.array([pt[1] for pt in results[param]])

            # Find nearest frequency index
            idx = np.argmin(np.abs(freqs - diag_freq))
            mag_db = 20 * np.log10(np.abs(complex_vals[idx]))
            diag[param] = round(mag_db, 3)
        return diag

    # ── CSV Logging ─────────────────────────────────────────────────────

    def _read_csv_rows(self):
        """Read all rows from the diagnostic CSV."""
        if not os.path.exists(CSV_FILE):
            return []
        with open(CSV_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_csv_rows(self, rows):
        """Write all rows to the diagnostic CSV."""
        fieldnames = [
            'part_number', 'current_draw_mA',
            'S11_dB', 'S21_dB', 'S12_dB', 'S22_dB',
            'timestamp'
        ]
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def part_number_exists_in_csv(self, part_number):
        """Check if a part number already has an entry in the CSV."""
        rows = self._read_csv_rows()
        return any(row['part_number'] == part_number for row in rows)

    def append_diagnostic(self, part_number, current_draw_ma, diag_values,
                          overwrite=False):
        """
        Append (or overwrite) a diagnostic entry in the CSV.

        Args:
            part_number: e.g. "LNA00001P1"
            current_draw_ma: current draw in milliamps
            diag_values: dict from get_diagnostic_values()
            overwrite: if True, replace existing entry for this part number
        """
        timestamp = datetime.datetime.now().isoformat(timespec='seconds')
        new_row = {
            'part_number': part_number,
            'current_draw_mA': current_draw_ma,
            'S11_dB': diag_values['S11'],
            'S21_dB': diag_values['S21'],
            'S12_dB': diag_values['S12'],
            'S22_dB': diag_values['S22'],
            'timestamp': timestamp,
        }

        rows = self._read_csv_rows()

        if overwrite:
            rows = [r for r in rows if r['part_number'] != part_number]

        rows.append(new_row)
        self._write_csv_rows(rows)


# ─── CLI Flow ──────────────────────────────────────────────────────────────

def print_banner():
    """Print the startup banner."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]LNA S-Parameter Measurement Tool[/]\n"
        "[dim]LibreVNA + LibreCAL • CASM Commissioning[/]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def print_sweep_config(start_freq, stop_freq, num_points, power, ifbw):
    """Display sweep configuration in a table."""
    table = Table(
        title="Sweep Configuration",
        box=box.ROUNDED,
        show_header=False,
        title_style="bold",
    )
    table.add_column("Parameter", style="dim")
    table.add_column("Value", style="bold cyan")

    table.add_row("Start Frequency", f"{start_freq / 1e6:.3f} MHz")
    table.add_row("Stop Frequency", f"{stop_freq / 1e6:.3f} MHz")
    table.add_row("Number of Points", str(int(num_points)))
    table.add_row("Stimulus Power", f"{power} dBm")
    table.add_row("IF Bandwidth", f"{ifbw / 1e3:.1f} kHz")
    table.add_row("Diagnostic Freq", f"{DIAGNOSTIC_FREQ / 1e6:.1f} MHz")
    table.add_row(
        "Highlight Band",
        f"{HIGHLIGHT_FREQ_RANGE[0]/1e6:.0f}–{HIGHLIGHT_FREQ_RANGE[1]/1e6:.0f} MHz"
    )

    console.print(table)
    console.print()


def print_diagnostic_table(part_number, current_draw, diag_values):
    """Display diagnostic results in a rich table."""
    table = Table(
        title=f"Diagnostics @ {DIAGNOSTIC_FREQ/1e6:.0f} MHz — {part_number}",
        box=box.HEAVY_EDGE,
        title_style="bold green",
    )
    table.add_column("Parameter", style="bold")
    table.add_column("Value (dB)", justify="right", style="cyan")

    for param in ["S11", "S21", "S12", "S22"]:
        val = diag_values[param]
        # Color-code: green for good gain (S21), yellow for moderate, red for bad
        if param == "S21":
            color = "green" if val > 33 else ("yellow" if val > 0 else "red")
        elif param in ("S11", "S22"):
            color = "green" if val < -10 else ("yellow" if val < -5 else "red")
        else:
            color = "cyan"
        table.add_row(param, f"[{color}]{val:.3f}[/]")

    table.add_row("Current Draw", f"[magenta]{current_draw} mA[/]")
    console.print(table)
    console.print()


def parse_frequency_input(value, default_hz):
    """Parse a frequency string like '100MHz', '2.5GHz', or raw Hz."""
    if not value or not str(value).strip():
        return default_hz

    value = str(value).strip().upper()
    multipliers = {'GHZ': 1e9, 'MHZ': 1e6, 'KHZ': 1e3, 'HZ': 1}

    for unit, mult in multipliers.items():
        if value.endswith(unit):
            try:
                number = float(value[:-len(unit)].strip())
                return number * mult
            except ValueError:
                pass

    try:
        return float(value)
    except ValueError:
        return default_hz


def step_connect(controller, headless=False):
    """Step 1: Connect to LibreVNA."""
    console.print("\n[bold]Step 1: Connect to LibreVNA[/]")
    
    if not headless:
        console.print(
            "  [bold yellow]Important Connection Steps:[/]\n"
            "  1. Plug in the LibreVNA via USB.\n"
            "  2. Open the [cyan]LibreVNA-GUI[/] application on your Mac.\n"
            "  3. Go to [cyan]Window → Preferences → General[/] and ensure the [cyan]SCPI Server[/] is checked (Port 19542).\n"
            "  4. Keep the GUI open in the background.\n"
        )
        console.input("  Press [bold]Enter[/] when you are ready to connect...")
    
    console.print(f"\n  Connecting to SCPI server at {VNA_HOST}:{VNA_PORT}...")

    try:
        dev = controller.connect()
        controller.set_vna_mode()
        console.print("  [green]✓ Connected and in VNA mode[/]\n")
        return True
    except ConnectionError as e:
        console.print(f"  [red]✗ {e}[/]\n")
        return False
    except Exception as e:
        console.print(f"  [red]✗ Connection failed: {e}[/]\n")
        return False


def step_fetch_sweep_config(controller):
    """Step 3: Fetch sweep parameters from the LibreVNA and allow modifying power."""
    console.print("[bold]Step 3: Fetching Sweep Parameters from Calibration[/]")
    
    try:
        start_freq = float(controller.vna.query(":VNA:FREQuency:START?"))
        stop_freq = float(controller.vna.query(":VNA:FREQuency:STOP?"))
        num_points = int(controller.vna.query(":VNA:ACQ:POINTS?"))
        power = float(controller.vna.query(":VNA:STIM:LVL?"))
        ifbw = float(controller.vna.query(":VNA:ACQ:IFBW?"))
    except Exception as e:
        console.print(f"  [yellow]⚠ Could not fetch sweep from GUI: {e}[/]")
        start_freq, stop_freq, num_points, power, ifbw = 10e6, 2e9, 101, float(DEFAULT_POWER), 1000.0
        
    # Allow user to modify stimulus power
    try:
        power_str = Prompt.ask(
            f"  Stimulus Power (dBm)",
            default=f"{power:.1f}"
        )
        new_power = float(power_str)
        if new_power != power:
            controller.vna.cmd(f":VNA:STIM:LVL {new_power}")
            power = new_power
            time.sleep(0.2)
    except Exception as e:
        console.print(f"  [yellow]⚠ Invalid power input, keeping {power:.1f} dBm[/]")

    controller.start_freq = start_freq
    controller.stop_freq = stop_freq
    controller.num_points = num_points
    controller.power = power
    controller.ifbw = ifbw

    print_sweep_config(start_freq, stop_freq, num_points, power, ifbw)
    return start_freq, stop_freq, num_points, power, ifbw


def step_enter_dut():
    """Step 4: Enter DUT information."""
    console.print("[bold]Step 4: Device Under Test[/]")

    while True:
        lna_str = Prompt.ask("  LNA number [00000-99999]")
        try:
            lna_num = validate_lna_number(lna_str)
            break
        except ValueError as e:
            console.print(f"  [red]{e}[/]")

    while True:
        pol_str = Prompt.ask("  Polarization [1 or 2]", choices=["1", "2"])
        polarization = int(pol_str)
        break

    part_number = make_part_number(lna_num, polarization)

    while True:
        curr_str = Prompt.ask("  Current draw (mA) [or 'short' / 'abort']")
        curr_str = curr_str.strip().upper()
        
        if curr_str in ("ABORT", "SHORT"):
            current_draw = curr_str
            break
            
        try:
            current_draw = float(curr_str)
            break
        except ValueError:
            console.print("  [red]Invalid input. Enter a number, 'short', or 'abort'.[/]")

    console.print(f"\n  Part number: [bold green]{part_number}[/]")
    if isinstance(current_draw, str):
        console.print(f"  Status: [bold red]{current_draw}[/]\n")
    else:
        console.print(f"  Current draw: [magenta]{current_draw} mA[/]\n")

    return part_number, current_draw

import threading

def step_verify_calibration(controller, manager, delay_p1, delay_p2):
    """Post-calibration verification step."""
    import select
    
    if not Confirm.ask("\n[bold]Run Live Post-Calibration Verification?[/]", default=True):
        return True
        
    console.print(
        "\n  [bold yellow]Live Verification Instructions:[/]\n"
        "  A native window will open. You can swap standards (OPEN, SHORT, THRU) live.\n"
        "  The window will update in real-time with your de-embedded measurements.\n"
        "  [bold]Press Enter in the terminal to stop.[/]"
    )
    
    plt.ion()
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.canvas.manager.set_window_title('Live Verification (De-embedded)')
    
    # Draw smith chart boundaries manually using rectangular plots for speed
    theta = np.linspace(0, 2*np.pi, 60)
    cx, cy = np.cos(theta), np.sin(theta)
    
    lines = {}
    for i, param in enumerate(['S11', 'S22']):
        axes[i].set_aspect('equal')
        axes[i].set_xlim(-1.1, 1.1)
        axes[i].set_ylim(-1.1, 1.1)
        axes[i].axis('off')
        axes[i].set_title(f"Live {param} (Smith)")
        axes[i].plot(cx, cy, color='gray', linestyle='--')
        axes[i].plot([-1, 1], [0, 0], color='gray', linestyle='--')
        line, = axes[i].plot([], [], marker='.', linestyle='none', color='magenta')
        lines[param] = line

    plt.show(block=False)
    
    # Temporarily drop VNA points for maximum live-view frame rate
    original_points = controller.num_points
    controller.vna.cmd(":VNA:ACQ:POINTS 51")
    time.sleep(0.2)
    
    try:
        from cal_manager import apply_port_extension
        while True:
            # Non-blocking check if Enter was pressed (macOS-safe, no threads)
            if select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                break
                
            try:
                results = controller.measure_single_sweep()
            except Exception:
                time.sleep(0.1)
                continue
            
            if results:
                # Apply port extensions mathematically in real-time
                if delay_p1 != 0.0 or delay_p2 != 0.0:
                    results = apply_port_extension(results, delay_p1, delay_p2)

                for param in ['S11', 'S22']:
                    c_vals = np.array([c for _, c in results[param]])
                    r_x = np.real(c_vals)
                    r_y = np.imag(c_vals)
                    lines[param].set_data(r_x, r_y)
                
                fig.canvas.draw_idle()
                fig.canvas.flush_events()
                
            plt.pause(0.05)
    except Exception as e:
        console.print(f"  [red]Live plot interrupted: {e}[/]")
        
    # Restore original calibration sweep points
    controller.vna.cmd(f":VNA:ACQ:POINTS {original_points}")
    time.sleep(0.2)
        
    plt.close(fig)
    plt.ioff()
    console.print("  [green]✓ Live Verification completed.[/]")
    return True

def step_measure(controller, part_number, delay_p1=0.0, delay_p2=0.0):
    """Step 5: Perform measurement."""
    console.print(f"[bold]Step 5: Measuring {part_number}[/]")

    # Double check stimulus power level before proceeding to prevent LNA damage
    target_power = controller.power if controller.power is not None else float(DEFAULT_POWER)
    try:
        current_power = float(controller.vna.query(":VNA:STIM:LVL?"))
        if abs(current_power - target_power) > 0.05:
            console.print(f"  [yellow]⚠ Stimulus power discrepancy detected (VNA: {current_power:.1f} dBm, Target: {target_power:.1f} dBm).[/]")
            console.print(f"  Correcting VNA stimulus power to {target_power:.1f} dBm...")
            controller.vna.cmd(f":VNA:STIM:LVL {target_power}")
            time.sleep(0.3)
            current_power = float(controller.vna.query(":VNA:STIM:LVL?"))
            
        if current_power > -39.9:
            console.print(f"  [red]✗ SAFETY ABORT: VNA power level is {current_power:.1f} dBm (unsafe for LNA, must be <= -40 dBm).[/]\n")
            return None
            
        console.print(f"  [green]✓ Confirmed stimulus power: {current_power:.1f} dBm[/]")
    except Exception as e:
        console.print(f"  [red]✗ Failed to verify VNA stimulus power: {e}[/]\n")
        return None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Triggering sweep...", total=100)

        progress.update(task, completed=10, description="Triggering sweep...")
        results = None
        try:
            # The measure_single_sweep method handles trigger + wait + data
            # We update progress manually for UX
            progress.update(task, completed=30, description="Waiting for sweep...")
            results = controller.measure_single_sweep()
            progress.update(task, completed=80, description="Processing data...")
            time.sleep(0.3)
            progress.update(task, completed=100, description="Complete!")
        except Exception as e:
            progress.update(task, completed=100, description=f"[red]Error: {e}[/]")
            console.print(f"\n  [red]✗ Measurement failed: {e}[/]\n")
            return None

    n_points = len(results["S11"])
    console.print(f"  [green]✓ Captured {n_points} points across 4 S-parameters[/]")
    
    # Apply port extensions
    if delay_p1 != 0.0 or delay_p2 != 0.0:
        results = apply_port_extension(results, delay_p1, delay_p2)
        console.print(f"  [green]✓ Applied port extensions (P1: {delay_p1}ps, P2: {delay_p2}ps)[/]")
    console.print()
        
    return results


def step_save_and_report(controller, manager, results, part_number,
                         current_draw, start_freq, stop_freq):
    """Steps 6-8: Save touchstone, plot, diagnostics, CSV."""

    console.print("[bold]Step 6: Saving Results[/]")

    # ── Touchstone ──
    s2p_path = manager.save_touchstone(
        results, part_number, start_freq, stop_freq
    )
    if s2p_path:
        console.print(f"  [green]✓ Touchstone:[/] {s2p_path}")

    # ── Plot ──
    png_path = manager.plot_s_parameters(results, part_number)
    console.print(f"  [green]✓ Plot:[/]       {png_path}")

    # ── Diagnostics ──
    console.print(f"\n[bold]Step 7: Diagnostics @ {DIAGNOSTIC_FREQ/1e6:.0f} MHz[/]")

    diag_values = manager.get_diagnostic_values(results)
    print_diagnostic_table(part_number, current_draw, diag_values)

    # ── CSV ──
    console.print("[bold]Step 8: Logging to CSV[/]")

    overwrite = False
    if manager.part_number_exists_in_csv(part_number):
        console.print(
            f"  [yellow]⚠ {part_number} already exists in the log[/]"
        )
        overwrite = Confirm.ask("  Overwrite existing entry?", default=True)
        if not overwrite:
            console.print("  [dim]Skipped CSV update[/]\n")
            return

    manager.append_diagnostic(
        part_number, current_draw, diag_values, overwrite=overwrite
    )
    console.print(f"  [green]✓ Logged to:[/]  {CSV_FILE}\n")


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="LNA S-Parameter Measurement Tool")
    parser.add_argument('--headless', action='store_true',
                        help='Run LibreVNA in headless mode (no GUI required)')
    args = parser.parse_args()

    print_banner()

    # Headless mode: auto-launch LibreVNA-GUI as background process
    vna_process = None
    if args.headless:
        console.print("[bold yellow]Starting LibreVNA in headless mode...[/]")
        try:
            vna_process = subprocess.Popen(
                ["/Applications/LibreVNA-GUI.app/Contents/MacOS/LibreVNA-GUI",
                 "--port", "19542", "--no-gui"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(3)
            console.print("[green]✓ Headless server running in background[/]")
        except Exception as e:
            console.print(f"[red]Failed to start LibreVNA headless: {e}[/]")
            sys.exit(1)

        def cleanup():
            if vna_process:
                vna_process.terminate()
                vna_process.wait()
        atexit.register(cleanup)

    # Preflight checks
    if not HAS_SKRF:
        console.print(
            "[yellow]⚠ scikit-rf not installed. "
            "Touchstone file saving will be disabled.[/]\n"
            "  Install with: [cyan]pip install scikit-rf[/]\n"
        )

    controller = LibreVNAController()
    manager = MeasurementManager()
    cal_manager = CalInstancesManager()

    # ── Step 1: Connect ──
    if not step_connect(controller, headless=args.headless):
        console.print("[red]Aborting. Fix connection and try again.[/]")
        sys.exit(1)

    # ── Step 2 & 3: Calibration and Verification Loop ──
    while True:
        cal_path, delay_p1, delay_p2, inst_name = cal_manager.interactive_menu(controller)
        if cal_path is False: # Aborted or failed
            console.print("[red]Aborting.[/]")
            controller.close()
            sys.exit(1)
        if cal_path is None:
            # Skip calibration
            pass

        # Fetch Sweep
        start_freq, stop_freq, num_points, power, ifbw = step_fetch_sweep_config(
            controller
        )
        
        # Verify
        if inst_name:
            # First verify with raw base calibration (no delays)
            console.print("\n  [bold cyan]Verifying Raw Base Calibration (No Delays)...[/]")
            step_verify_calibration(controller, manager, 0.0, 0.0)
            
            # Now ask if they want to apply port extension
            if Confirm.ask("\n  Apply port extension / de-embedding?", default=True):
                use_saved = True
                
                # If delays are 0.0 (newly created or reset instance), compute them directly
                if delay_p1 == 0.0 and delay_p2 == 0.0:
                    console.print("\n  [bold cyan]No saved port delays found. Proceeding to compute delays...[/]")
                    from cal_manager import compute_delay_from_reflection
                    delay_p1, delay_p2 = cal_manager._run_deembedding_flow(
                        controller, delay_p1, delay_p2
                    )
                    cal_manager.instances[inst_name]['port1_delay_ps'] = delay_p1
                    cal_manager.instances[inst_name]['port2_delay_ps'] = delay_p2
                    cal_manager._save()
                    console.print(f"  [green]✓ Updated delays saved to '{inst_name}'.[/]\n")
                    use_saved = False

                while True:
                    if use_saved:
                        console.print(f"  [green]✓ Applying saved delays: P1={delay_p1:.2f}ps, P2={delay_p2:.2f}ps[/]")
                    
                    console.print("\n  [bold cyan]Verifying De-embedded Calibration...[/]")
                    step_verify_calibration(controller, manager, delay_p1, delay_p2)
                    
                    # Ask if they want to re-compute
                    if Confirm.ask("\n  Re-compute de-embedding delays for this instance?", default=False):
                        from cal_manager import compute_delay_from_reflection
                        delay_p1, delay_p2 = cal_manager._run_deembedding_flow(
                            controller, delay_p1, delay_p2
                        )
                        cal_manager.instances[inst_name]['port1_delay_ps'] = delay_p1
                        cal_manager.instances[inst_name]['port2_delay_ps'] = delay_p2
                        cal_manager._save()
                        console.print(f"  [green]✓ Updated delays saved to '{inst_name}'.[/]\n")
                        use_saved = False
                        continue
                    break
            else:
                # User chose not to apply port extension
                delay_p1 = 0.0
                delay_p2 = 0.0
            break
        else:
            # Skip calibration
            step_verify_calibration(controller, manager, delay_p1, delay_p2)
            break
            
    # ── Measurement Loop ──
    try:
        while True:
            console.rule("[bold cyan]New Measurement[/]", style="cyan")

            # ── Step 4: DUT Info ──
            part_number, current_draw = step_enter_dut()
            
            if current_draw == "ABORT":
                console.print("  [yellow]⚠ Measurement aborted. Skipping...[/]\n")
                continue
                
            if current_draw == "SHORT":
                console.print(f"  [red]⚠ Logging {part_number} as SHORT.[/]\n")
                manager.append_diagnostic(
                    part_number, 
                    "SHORT", 
                    {"S11": float('nan'), "S21": float('nan'), "S12": float('nan'), "S22": float('nan')},
                    overwrite=manager.part_number_exists_in_csv(part_number)
                )
                continue

            # Check for duplicate
            if manager.part_number_exists_in_csv(part_number):
                console.print(
                    f"  [yellow]⚠ {part_number} was previously measured.[/]"
                )
                if not Confirm.ask("  Measure again?", default=True):
                    continue

            # ── Step 5: Measure ──
            results = step_measure(controller, part_number, delay_p1, delay_p2)
            if results is None:
                if Confirm.ask("  Retry measurement?", default=True):
                    continue
                else:
                    break

            # ── Steps 6-8: Save, Plot, Log ──
            step_save_and_report(
                controller, manager, results,
                part_number, current_draw,
                start_freq, stop_freq
            )

            # ── Step 9: Continue? ──
            console.print()
            if not Confirm.ask(
                "[bold]Measure another device?[/]", default=True
            ):
                break

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/]")
    finally:
        controller.close()
        console.print("\n[dim]Connection closed. Goodbye![/]\n")


if __name__ == "__main__":
    main()
