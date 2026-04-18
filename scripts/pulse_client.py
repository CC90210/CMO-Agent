import json
import os
import datetime
from pathlib import Path

# The pulse directory is centralized in the CEO's (Bravo's) repository to act as the board room table.
PULSE_DIR = Path(r"C:\Users\User\Business-Empire-Agent\data\pulse")
CMO_PULSE_PATH = PULSE_DIR / "cmo_pulse.json"
CEO_PULSE_PATH = PULSE_DIR / "ceo_pulse.json"
CFO_PULSE_PATH = PULSE_DIR / "cfo_pulse.json"

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
        Checks cfo_pulse.json to see if Atlas has approved the spend.
        """
        cfo_pulse = self.get_cfo_pulse()
        # Atlas will set this boolean in cfo_pulse.json when approving
        return cfo_pulse.get("spend_approved_by_atlas", False)

if __name__ == "__main__":
    # Test script functionality
    client = PulseClient()
    print("CEO Pulse:", client.get_ceo_pulse().get('status', 'Not found'))
    print("CMO Pulse Updated:", client.update_cmo_pulse({"status": "ACTIVE"}).get('status'))
