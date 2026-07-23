"""
Utilities for Siglent SSA3032X Plus (single + python-averaged trace)

- Set fstart/fstop/RBW/detector/preamp/attenuation
- Read back key settings
- Force instrument averaging OFF so Python controls averaging
- Acquire trace (display trace values; typically dBm)
- Save NPZ: <base>_<hot|cold>_.npz  (no timestamp in filename)
"""

import json
import datetime
import pyvisa
import numpy as np


# ---------- CLI helpers ----------

def pick_resource():
    rm = pyvisa.ResourceManager()
    instruments = rm.list_resources()
    if not instruments:
        raise SystemExit("No VISA instruments found.")

    print("Available VISA resources:")
    for idx, res in enumerate(instruments):
        print(f"  [{idx}] {res}")

    while True:
        try:
            choice = int(input("Select resource number: "))
            if 0 <= choice < len(instruments):
                return instruments[choice]
        except ValueError:
            pass
        print("Invalid selection. Try again.")


def _prompt_keep_current(prompt):
    s = input(prompt).strip()
    return None if s == "" else s


def prompt_sa_settings(include_avg=False):
    """
    Blank input keeps the instrument's current setting.
    Detector examples for Siglent: POS, NEG, SAMP, AVER
    """
    print("\nEnter settings (blank = keep instrument's current setting).")

    fstart = _prompt_keep_current("Start frequency (e.g., 375MHz) [blank=keep]: ")
    fstop  = _prompt_keep_current("Stop  frequency (e.g., 500MHz) [blank=keep]: ")
    rbw    = _prompt_keep_current("RBW (e.g., 10kHz, 1MHz) [blank=keep]: ")

    detector = _prompt_keep_current("Detector (POS, NEG, SAMP, AVER) [blank=keep]: ")
    if detector is not None:
        detector = detector.strip().upper()

    preamp = None
    preamp_input = input("Enable preamp? (y/n, blank=keep): ").strip().lower()
    if preamp_input == "y":
        preamp = True
    elif preamp_input == "n":
        preamp = False

    att = None
    att_input = input("Input attenuation in dB (blank=keep): ").strip()
    if att_input:
        try:
            att = float(att_input)
        except ValueError:
            print("Invalid attenuation value. Keeping current.")

    n_avg = None
    avg_mode = None
    if include_avg:
        n_avg_str = (input("Number of traces to average [default 4]: ").strip() or "4")
        try:
            n_avg = int(n_avg_str)
            if n_avg < 1:
                raise ValueError
        except ValueError:
            print("Invalid n_avg; using 4.")
            n_avg = 4

        avg_mode = (input("Average mode: [power] (recommended) or dbm: ").strip().lower()
                    or "power")
        if avg_mode not in ("power", "dbm"):
            print("Invalid average mode; using 'power'.")
            avg_mode = "power"

    return {
        "fstart": fstart,
        "fstop": fstop,
        "rbw": rbw,
        "detector": detector,
        "preamp": preamp,
        "att": att,
        "n_avg": n_avg,
        "avg_mode": avg_mode,
    }


# ---------- Conversions for averaging ----------

def dbm_to_mw(dbm):
    dbm = np.asarray(dbm, dtype=np.float64)
    return 10.0 ** (dbm / 10.0)


def mw_to_dbm(mw):
    mw = np.asarray(mw, dtype=np.float64)
    mw = np.maximum(mw, 1e-30)
    return 10.0 * np.log10(mw)


def utc_timestamp_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------- Instrument wrapper (Siglent SSA3032X Plus) ----------

class SpectrumAnalyzer:
    def __init__(self, resource, timeout_ms=60000):
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource)

        # For TCPIP instruments, give generous defaults.
        self.inst.timeout = timeout_ms
        self.inst.write_termination = "\n"
        self.inst.read_termination = "\n"

        # Increase chunk size for faster reads (pyvisa/pyvisa-py)
        try:
            self.inst.chunk_size = 1024 * 1024
        except Exception:
            pass

        idn = self.safe_query("*IDN?", timeout_ms=5000) or "UNKNOWN"
        print(f"Connected to: {idn}")

        self._trace_cmd = None  # chosen trace query command
        self.drain_errors()
    
    def drain_errors(self, max_reads=20):
        for _ in range(max_reads):
            e = self.safe_query("SYST:ERR?", timeout_ms=2000)
            if not e or e.startswith("0"):
                return
            
    def close(self):
        try:
            self.inst.close()
        finally:
            try:
                self.rm.close()
            except Exception:
                pass

    def safe_write(self, cmd):
        try:
            self.inst.write(cmd)
            return True
        except Exception as e:
            print(f"Write failed: {cmd} ({e})")
            return False

    def safe_query(self, cmd, timeout_ms=None):
        old = self.inst.timeout
        if timeout_ms is not None:
            self.inst.timeout = timeout_ms
        try:
            return self.inst.query(cmd).strip()
        except Exception:
            return None
        finally:
            self.inst.timeout = old

    def safe_query_float(self, cmd, timeout_ms=None):
        s = self.safe_query(cmd, timeout_ms=timeout_ms)
        if s is None:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def check_error(self, label=""):
        err = self.safe_query("SYST:ERR?", timeout_ms=3000)
        if err and not err.startswith("0"):
            if label:
                print(f"SYST:ERR? after {label}: {err}")
            else:
                print(f"SYST:ERR?: {err}")
        return err

    # ----- Configuration -----

    def setup(self, fstart=None, fstop=None, rbw=None, detector=None, preamp=None, att=None):
        self.drain_errors()
        if fstart is not None:
            self.safe_write(f":SENSe:FREQuency:STARt {fstart}")
        if fstop is not None:
            self.safe_write(f":SENSe:FREQuency:STOP {fstop}")

        if rbw is not None:
            self.safe_write(":SENSe:BWIDth:RESolution:AUTO OFF")
            self.safe_write(f":SENSe:BWIDth:RESolution {rbw}")

        if detector is not None:
            self.safe_write(f":SENSe:DETector:TRACe1:FUNCtion {detector}")

        # correct preamp command for your SSA
        if preamp is not None:
            self.safe_write(f":SENSe:POWer:RF:GAIN:STATe {'ON' if preamp else 'OFF'}")

        if att is not None:
            self.safe_write(":SENSe:POWer:ATTenuation:AUTO OFF")
            self.safe_write(f":SENSe:POWer:ATTenuation {att}")

        self.check_error("setup")

    def force_python_averaging(self, verbose=True):
        """
        Disable analyzer internal averaging so each INIT is one sweep,
        and force trigger to immediate so INIT doesn't wait forever.
        """
        self.drain_errors()
        # data format for query_ascii_values
        self.safe_write(":FORMat ASCii")

        # single-sweep style control
        self.safe_write(":INITiate:CONTinuous OFF")

        # Ensure we don't wait on external triggers
        # (Different firmware may accept one or the other)
        self.safe_write(":TRIGger:SEQuence:SOURce IMMediate")
        self.safe_write(":TRIG:SOUR IMM")

        # Trace mode normal write/update
        self.safe_write(":TRACe1:MODE WRITe")

        # Disable averaging
        self.safe_write(":SENSe:AVERage:STATe OFF")
        self.safe_write(":SENSe:AVERage:TRACe1:STATe OFF")
        self.safe_write(":SENSe:AVERage:TRACe1:COUNt 1")


        self.check_error("force_python_averaging")

        # Detect correct trace query once (avoids repeated slow failures)
        self._detect_trace_command()

        if verbose:
            st = self.safe_query(":SENSe:AVERage:TRACe1:STATe?", timeout_ms=3000)
            ct = self.safe_query(":SENSe:AVERage:TRACe1:COUNt?", timeout_ms=3000)
            md = self.safe_query(":TRACe1:MODE?", timeout_ms=3000)
            trig = (self.safe_query(":TRIGger:SEQuence:SOURce?", timeout_ms=3000)
                    or self.safe_query(":TRIG:SOUR?", timeout_ms=3000))
            print(f"Instrument averaging now: state={st}, count={ct}, trace_mode={md}, trig={trig}")
            print(f"Using trace query command: {self._trace_cmd}")

    # ----- Readback -----

    def readback_settings(self):
        s = {}
        s["idn"] = self.safe_query("*IDN?", timeout_ms=5000) or ""
        s["fstart_hz"] = self.safe_query_float(":SENSe:FREQuency:STARt?", timeout_ms=3000)
        s["fstop_hz"]  = self.safe_query_float(":SENSe:FREQuency:STOP?", timeout_ms=3000)
        s["rbw_hz"]    = self.safe_query_float(":SENSe:BWIDth:RESolution?", timeout_ms=3000)
        s["sweep_time_s"] = self.safe_query_float(":SENSe:SWEep:TIME?", timeout_ms=3000)
        s["sweep_points"] = self.safe_query_float(":SENSe:SWEep:POINts?", timeout_ms=3000)
        s["attenuation_db"] = self.safe_query_float(":SENSe:POWer:ATTenuation?", timeout_ms=3000)
        s["preamp_state"] = self.safe_query(":SENSe:POWer:RF:GAIN:STATe?", timeout_ms=3000)
        s["detector"] = self.safe_query(":SENSe:DETector:TRACe1:FUNCtion?", timeout_ms=3000)
        s["avg_state"] = self.safe_query(":SENSe:AVERage:TRACe1:STATe?", timeout_ms=3000)
        s["avg_count"] = self.safe_query(":SENSe:AVERage:TRACe1:COUNt?", timeout_ms=3000)
        s["trace1_mode"] = self.safe_query(":TRACe1:MODE?", timeout_ms=3000)
        return s

    def print_settings(self, title="Instrument settings"):
        s = self.readback_settings()
        print(f"\n--- {title} ---")
        for k in sorted(s.keys()):
            print(f"{k:>16}: {s[k]}")
        return s

    # ----- Trace query detection + acquisition -----

    def _try_query_ascii_values(self, cmd, timeout_ms=3000):
        old = self.inst.timeout
        self.inst.timeout = timeout_ms
        try:
            vals = self.inst.query_ascii_values(cmd)
            return np.array(vals, dtype=np.float64)
        finally:
            self.inst.timeout = old

    def _detect_trace_command(self):
        """
        Find a trace read command your firmware supports, and save it.
        This avoids long delays from trying unsupported headers between traces.
        """
        if self._trace_cmd is not None:
            return self._trace_cmd

        # Ensure a sweep has happened so trace exists
        self._single_sweep_wait()

        candidates = [
            ":TRACe:DATA:SPECtrum?",
            ":TRACe:SPECtrum?",
            ":TRACe:SPEC?",
            ":TRACe1:DATA?",
        ]

        last_err = None
        for cmd in candidates:
            try:
                data = self._try_query_ascii_values(cmd, timeout_ms=3000)
                if data.size > 0:
                    self._trace_cmd = cmd
                    return cmd
            except Exception as e:
                last_err = e

        raise RuntimeError(f"Could not detect trace query command. Last error: {last_err}")

    def _single_sweep_wait(self):
        """
        Reliable sweep completion wait using *OPC? (not *WAI).
        """
        # Timeout should be generous; sweep time can vary
        # Use current inst.timeout
        r = self.safe_query(":INITiate:IMMediate;*OPC?", timeout_ms=self.inst.timeout)
        if r is None:
            # fallback: write then query
            self.safe_write(":INITiate:IMMediate")
            _ = self.safe_query("*OPC?", timeout_ms=self.inst.timeout)

    def _read_trace(self):
        if self._trace_cmd is None:
            self._detect_trace_command()
        vals = self.inst.query_ascii_values(self._trace_cmd)
        return np.array(vals, dtype=np.float64)

    def acquire_trace(self):
        """
        Returns:
          freq_hz (np.ndarray), trace_dbm (np.ndarray)
        """
        # wait for sweep complete
        self._single_sweep_wait()

        # read trace
        data = self._read_trace()

        # freq axis
        fstart = self.safe_query_float(":SENSe:FREQuency:STARt?", timeout_ms=3000)
        fstop  = self.safe_query_float(":SENSe:FREQuency:STOP?", timeout_ms=3000)
        if fstart is None or fstop is None:
            freq = np.arange(data.size, dtype=np.float64)
        else:
            freq = np.linspace(fstart, fstop, data.size)

        return freq, data

    def acquire_trace_data_only(self):
        self._single_sweep_wait()
        return self._read_trace()


# ---------- Averaging + Save ----------

def acquire_averaged_trace(sa: SpectrumAnalyzer, n_avg: int, avg_mode: str = "power"):
    """
    avg_mode:
      - 'power': convert dBm->mW, average, convert back to dBm (recommended)
      - 'dbm'  : average directly in dBm
    """
    freq, first = sa.acquire_trace()

    if avg_mode == "power":
        acc = dbm_to_mw(first)
        for i in range(1, n_avg):
            print(f"Trace {i+1}/{n_avg}", flush=True)
            d = sa.acquire_trace_data_only()
            acc += dbm_to_mw(d)
        acc /= n_avg
        avg_trace_dbm = mw_to_dbm(acc)
    else:
        acc = first.astype(np.float64)
        for i in range(1, n_avg):
            print(f"Trace {i+1}/{n_avg}", flush=True)
            d = sa.acquire_trace_data_only()
            acc += d
        avg_trace_dbm = acc / n_avg

    return freq, avg_trace_dbm


def save_npz(base_name, hot_cold, freq_hz, trace_dbm, metadata: dict, overwrite=False):
    """
    Saves: <base>_<hot|cold>_.npz   (no timestamp in filename)
    """
    base_name = (base_name or "").strip()
    hot_cold = (hot_cold or "").strip().lower()

    if not base_name:
        raise ValueError("base_name must be non-empty")
    if hot_cold not in ("hot", "cold"):
        raise ValueError("hot_cold must be 'hot' or 'cold'")

    fname = f"{base_name}_{hot_cold}_.npz"

    import os
    if os.path.exists(fname) and not overwrite:
        raise FileExistsError(f"{fname} already exists (set overwrite=True or choose a new base name).")

    meta_json = json.dumps(metadata, indent=2, sort_keys=True)
    np.savez(fname, freq_hz=freq_hz, trace_dbm=trace_dbm, metadata_json=meta_json)

    print(f"Saved: {fname}")
    return fname