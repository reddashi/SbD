# irr_full_cycle_demo.py
# ------------------------------------------------------------
# Shows both actuators: DRY → PUMP, WET → DRAIN in one run.

import threading
from gh import IrrigationPLC          # gh.py with bidirectional class

# --- Fast cadence so the whole demo fits in ~60 s -------------
import gh
gh.INTERVAL = 0.4                     # seconds per tick

def print_sender(msg):
    print(f"{msg['moisture']:6.2f}%   "
          f"pump={msg['pump_pct']:5.1f}%   "
          f"drain={msg['drain_pct']:5.1f}%")

plc = IrrigationPLC(
    sender=print_sender,
    initial_moisture=70,      # starts above MAX_MOISTURE → drain first
    dry_drift=0.5,            # slow natural evaporation
    irrigation_rate=4.0,      # pump adds water fast enough to see effect
    drain_rate=6.0            # drain removes water briskly for demo
)

# 150 cycles × 0.4 s ≈ 60 s = enough time for drain ↓ then pump ↑
thread = threading.Thread(target=plc.run, kwargs={"cycles": 150})
thread.start()
thread.join()

print("\nDemo complete: drain corrected high moisture; pump corrected low moisture.")