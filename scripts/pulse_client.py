import json
import datetime
from pathlib import Path

# Each agent owns its own pulse directory. Maven and Bravo read from the
# canonical paths (which are NOT all under one repo). Override per-machine
# via env vars MAVEN_PULSE_DIR / CEO_PULSE_PATH / CFO_PULSE_PATH if needed.
PULSE_DIR = Path(r"C:\Users\User\CMO-Agent\data\pulse")
CMO_PULSE_PATH = PULSE_DIR / "cmo_pulse.json"
CEO_PULSE_PATH = Path(r"C:\Users\User\Business-Empire-Agent\data\pulse\ceo_pulse.json")
# Atlas (CFO) writes to CFO-Agent/data/pulse — fixed 2026-04-26 to match
# brain/CFO_PULSE_CONTRACT.md in Atlas's repo.
CFO_PULSE_PATH = Path(r"C:\Users\User\APPS\CFO-Agent\data\pulse\cfo_pulse.json")

class PulseClient:
    """
    Client for the 3-Way C-Suite Pulse Protocol.
    Maven (CMO) uses this to read CEO/CFO pulses and update its own CMO pulse.
    """
    
    @staticmethod
    def _read_json(filepath: Path) -> dict:
        if not filepath.exists():
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _write_json(filepath: Path, data: dict):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_ceo_pulse(self) -> dict:
        """Reads Bravo's strategy and brand priorities."""
        return self._read_json(CEO_PULSE_PATH)

    def get_cfo_pulse(self) -> dict:
        """Reads Atlas's spend gates and runway."""
        return self._read_json(CFO_PULSE_PATH)

    def get_cmo_pulse(self) -> dict:
        """Reads Maven's current pulse state."""
        return self._read_json(CMO_PULSE_PATH)

    def update_cmo_pulse(self, updates: dict) -> dict:
        """
        Updates the CMO pulse with new data (e.g., ad spend requests, brand health).
        Per the protocol, Maven ONLY writes to its own pulse file.
        """
        pulse = self.get_cmo_pulse()
        
        # Helper to recursively update dictionaries
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    deep_update(d[k], v)
                else:
                    d[k] = v
                    
        deep_update(pulse, updates)
        pulse['updated_at'] = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        
        self._write_json(CMO_PULSE_PATH, pulse)
        return pulse

    def request_spend_approval(self, amount_cad: float, reason: str) -> bool:
        """
        Helper method to request spend approval from Atlas (CFO).
        Sets the spend_request_cad in cmo_pulse.json so Atlas can read it.
        """
        self.update_cmo_pulse({
            "spend_request_cad": amount_cad,
            "blocker_ceo_needs_to_know": f"Awaiting Atlas approval for {amount_cad} CAD ad spend. Reason: {reason}"
        })
        return True

    def check_spend_approval(self) -> bool:
        """
        Checks Atlas's cfo_pulse.json to see if the spend gate is open.

        Atlas uses a nested `spend_gate` object — see
        c:/Users/User/APPS/CFO-Agent/brain/CFO_PULSE_CONTRACT.md.
        Approved iff status == 'open'. The legacy boolean
        `spend_approved_by_atlas` was never written by Atlas — kept as a
        no-op fallback so this stays back-compatible.
        """
        cfo_pulse = self.get_cfo_pulse()
        spend_gate = cfo_pulse.get("spend_gate") or {}
        if isinstance(spend_gate, dict):
            return spend_gate.get("status") == "open"
        # v0 string form (deprecated 2026-04-26)
        return spend_gate == "open"

if __name__ == "__main__":
    # Test script functionality
    client = PulseClient()
    print("CEO Pulse:", client.get_ceo_pulse().get('status', 'Not found'))
    print("CMO Pulse Updated:", client.update_cmo_pulse({"status": "ACTIVE"}).get('status'))
