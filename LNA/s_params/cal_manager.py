import os
import json
import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm, FloatPrompt
from rich.table import Table

console = Console()

class CalInstancesManager:
    """Manages saved calibration instances and their port extensions (de-embedding)."""
    
    def __init__(self, json_path="cal_instances.json"):
        self.json_path = json_path
        self.instances = self._load()

    def _load(self):
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r') as f:
                    data = json.load(f)
                    return data.get("instances", {})
            except json.JSONDecodeError:
                return {}
        return {}

    def _save(self):
        with open(self.json_path, 'w') as f:
            json.dump({"instances": self.instances}, f, indent=4)

    def interactive_menu(self, controller):
        """
        Interactive rich menu to select or create a calibration instance.
        Returns:
            (cal_file_path, port1_delay_ps, port2_delay_ps)
        """
        console.print("[bold]Step 2: Calibration Instance[/]")
        
        choices = ["1", "2", "3", "4", "5"]
        
        while True:
            console.print(
                "  [cyan]1[/] — Load a saved Calibration Instance (with de-embedding)\n"
                "  [cyan]2[/] — Create a new Calibration Instance\n"
                "  [cyan]3[/] — Skip (No calibration)\n"
                "  [cyan]4[/] — Delete a Calibration Instance\n"
                "  [cyan]5[/] — Clear all Calibration Instances"
            )
            choice = Prompt.ask("  Select option", choices=choices, default="1")
            
            if choice == "3":
                return None, 0.0, 0.0, None
                
            if choice == "1":
                if not self.instances:
                    console.print("  [yellow]⚠ No saved instances found. Please create one.[/]\n")
                    continue
                    
                table = Table(title="Saved Calibration Instances")
                table.add_column("Name", style="bold cyan")
                table.add_column("Created", style="dim")
                table.add_column("File")
                table.add_column("P1 Delay (ps)")
                table.add_column("P2 Delay (ps)")
                
                names = list(self.instances.keys())
                console.print(f"\n  [bold]Select Instance to Load:[/]")
                for i, n in enumerate(names, 1):
                    console.print(f"  [cyan]{i}[/] — {n}")
                console.print(f"  [cyan]0[/] — Cancel")
                
                idx_str = Prompt.ask("  Select option", choices=[str(i) for i in range(len(names)+1)], default="0")
                if idx_str == "0":
                    continue
                    
                sel = names[int(idx_str)-1]
                inst = self.instances[sel]
                cal_file = os.path.expanduser(inst["cal_file_path"])
                
                try:
                    controller.load_calibration(cal_file)
                    console.print(f"  [green]✓ Base calibration loaded ({cal_file})[/]")
                except Exception as e:
                    console.print(f"  [red]✗ Failed to load calibration: {e}[/]\n")
                    continue
                
                console.print(f"  Saved Port extensions: P1={inst['port1_delay_ps']:.2f}ps, P2={inst['port2_delay_ps']:.2f}ps")

                return cal_file, inst["port1_delay_ps"], inst["port2_delay_ps"], sel
                    
            if choice == "4":
                if not self.instances:
                    console.print("  [yellow]⚠ No saved instances found to delete.[/]\n")
                    continue
                names = list(self.instances.keys())
                console.print(f"\n  [bold]Select Instance to Delete:[/]")
                for i, n in enumerate(names, 1):
                    console.print(f"  [cyan]{i}[/] — {n}")
                console.print(f"  [cyan]0[/] — Cancel")
                
                idx_str = Prompt.ask("  Select option", choices=[str(i) for i in range(len(names)+1)], default="0")
                if idx_str == "0":
                    continue
                    
                del_name = names[int(idx_str)-1]
                if Confirm.ask(f"  Are you sure you want to delete '{del_name}'?"):
                    del self.instances[del_name]
                    self._save()
                    console.print(f"  [green]✓ Instance '{del_name}' deleted.[/]\n")
                continue

            if choice == "5":
                if not self.instances:
                    console.print("  [yellow]⚠ No saved instances to clear.[/]\n")
                    continue
                n = len(self.instances)
                if Confirm.ask(f"  Are you sure you want to delete ALL {n} instance(s)?", default=False):
                    self.instances = {}
                    self._save()
                    console.print("  [green]✓ All calibration instances cleared.[/]\n")
                continue

            if choice == "2":
                name = Prompt.ask("  Name for this new instance (e.g. 'SMA_Adapter_Setup')")
                if name in self.instances:
                    console.print(f"  [red]✗ Instance name '{name}' already exists. Please choose a different name.[/]\n")
                    continue
                
                cal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cal_files")
                os.makedirs(cal_dir, exist_ok=True)
                
                cal_files = [f for f in os.listdir(cal_dir) if f.endswith(".cal")]
                if not cal_files:
                    console.print(f"  [yellow]⚠ No .cal files found in {cal_dir}[/]")
                    console.print("  [yellow]Please save your calibration from LibreVNA-GUI into that directory first.[/]\n")
                    continue
                
                console.print(f"\n  [bold]Select Base Calibration File from cal_files/[/]")
                for i, f in enumerate(cal_files, 1):
                    console.print(f"  [cyan]{i}[/] — {f}")
                
                f_idx = Prompt.ask("  Select file", choices=[str(i) for i in range(1, len(cal_files)+1)])
                cal_path = os.path.join(cal_dir, cal_files[int(f_idx)-1])
                
                try:
                    controller.load_calibration(cal_path)
                    console.print(f"  [green]✓ Base calibration loaded[/]")
                except Exception as e:
                    console.print(f"  [red]✗ Failed to load calibration: {e}[/]\n")
                    continue
                
                self.instances[name] = {
                    "timestamp": datetime.datetime.now().isoformat(timespec='minutes'),
                    "cal_file_path": cal_path,
                    "port1_delay_ps": 0.0,
                    "port2_delay_ps": 0.0
                }
                self._save()
                
                console.print(f"\n  [green]✓ Instance '{name}' saved successfully![/]\n")
                return cal_path, 0.0, 0.0, name

    def _run_deembedding_flow(self, controller, current_p1, current_p2):
        p1 = current_p1
        p2 = current_p2
        port_choice = Prompt.ask("  Which port?", choices=["1", "2", "both"], default="1")
        
        if port_choice in ["1", "both"]:
            console.print("\n  [bold yellow]Port 1 De-embedding:[/]")
            Prompt.ask("  Attach an OPEN or SHORT to the end of the Port 1 adapter and press Enter")
            
            try:
                console.print("  Averaging 3 sweeps for stability...")
                s11_avg = None
                for i in range(3):
                    results = controller.measure_single_sweep()
                    s11_data = np.array([c for _, c in results['S11']])
                    s11_avg = s11_data if s11_avg is None else s11_avg + s11_data
                s11_avg /= 3
                freqs = np.array([f for f, _ in results['S11']])
                p1 = compute_delay_from_reflection(freqs, s11_avg)
                console.print(f"  [green]✓ Computed Port 1 Delay: {p1:.2f} ps[/]")
            except Exception as e:
                console.print(f"  [red]✗ Failed to measure: {e}[/]")
                
        if port_choice in ["2", "both"]:
            console.print("\n  [bold yellow]Port 2 De-embedding:[/]")
            Prompt.ask("  Attach an OPEN or SHORT to the end of the Port 2 adapter and press Enter")
            
            try:
                console.print("  Averaging 3 sweeps for stability...")
                s22_avg = None
                for i in range(3):
                    results = controller.measure_single_sweep()
                    s22_data = np.array([c for _, c in results['S22']])
                    s22_avg = s22_data if s22_avg is None else s22_avg + s22_data
                s22_avg /= 3
                freqs = np.array([f for f, _ in results['S22']])
                p2 = compute_delay_from_reflection(freqs, s22_avg)
                console.print(f"  [green]✓ Computed Port 2 Delay: {p2:.2f} ps[/]")
            except Exception as e:
                console.print(f"  [red]✗ Failed to measure: {e}[/]")
        return p1, p2

import numpy as np

def compute_delay_from_reflection(freqs, s_complex):
    """
    Computes electrical delay (picoseconds) by unwrapping phase of a reflection measurement.
    Uses magnitude-weighted fitting and discards noisy low-magnitude points to be
    robust against noise floor contamination.
    """
    magnitude = np.abs(s_complex)
    
    # Only use points where the signal is within 20 dB of the peak
    # (noise floor points have random phase and will corrupt the fit)
    mag_db = 20 * np.log10(magnitude + 1e-12)
    threshold_db = np.max(mag_db) - 20.0
    good = mag_db >= threshold_db
    
    if np.sum(good) < 10:
        # Fall back to all points if too many are filtered
        good = np.ones(len(freqs), dtype=bool)
    
    freqs_f = freqs[good]
    phase = np.unwrap(np.angle(s_complex[good]))
    weights = magnitude[good]  # weight by magnitude — noisier points get less influence
    
    # Weighted linear fit: phase = m * f + c
    # Using numpy's weighted least squares via W = diag(weights)
    W = weights
    Wsum = np.sum(W)
    Wf = np.sum(W * freqs_f)
    Wf2 = np.sum(W * freqs_f**2)
    Wp = np.sum(W * phase)
    Wfp = np.sum(W * freqs_f * phase)
    
    denom = Wsum * Wf2 - Wf**2
    if abs(denom) < 1e-30:
        # Degenerate case, fall back to unweighted
        m, _ = np.polyfit(freqs_f, phase, 1)
    else:
        m = (Wsum * Wfp - Wf * Wp) / denom
    
    # m = -4 * pi * tau  (round-trip delay for reflection)
    tau = -m / (4 * np.pi)
    return tau * 1e12  # convert to ps

def apply_port_extension(results, delay_p1_ps, delay_p2_ps):
    """
    Apply mathematical port extensions (de-embedding) to raw S-parameters.
    results: dict of {param: [(freq, complex), ...]}
    delay_p1_ps: electrical delay to de-embed on Port 1 in picoseconds
    delay_p2_ps: electrical delay to de-embed on Port 2 in picoseconds
    
    Returns: new results dict with phase rotations applied
    """
    if delay_p1_ps == 0.0 and delay_p2_ps == 0.0:
        return results
        
    t1 = delay_p1_ps * 1e-12
    t2 = delay_p2_ps * 1e-12
    
    # We assume all parameters have the same frequency points
    freqs = np.array([f for f, _ in results.get('S11', [])])
    if len(freqs) == 0:
        return results

    omega = 2 * np.pi * freqs
    phase1 = omega * t1
    phase2 = omega * t2
    
    s_ext = {}
    
    for param in results:
        # Extract the complex values
        c_vals = np.array([c for _, c in results[param]])
        
        if param == 'S11':
            c_vals = c_vals * np.exp(1j * 2 * phase1)
        elif param == 'S22':
            c_vals = c_vals * np.exp(1j * 2 * phase2)
        elif param in ('S21', 'S12'):
            c_vals = c_vals * np.exp(1j * (phase1 + phase2))
            
        # Re-pack into list of tuples
        s_ext[param] = list(zip(freqs, c_vals))
        
    return s_ext
