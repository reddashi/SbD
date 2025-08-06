from gh import TemperaturePLC
import threading
import random

def print_sender(payload: dict) -> None:
    """
    Very simple 'channel' that just prints whatever the PLC sends.
    Replace this with a queue.put(), socket.send(), etc. when you integrate.
    """
    print(payload)

class SpikyTempPLC(TemperaturePLC):
    def _tick_environment(self):
        super()._tick_environment()
        if random.random() < 0.20:
            self.temp += random.uniform(-5, 5)

def print_sender(msg):               # simple channel
    print(msg)

plc = SpikyTempPLC(sender=print_sender, drift=0.4)
plc.run(cycles=20)

# Instantiate the PLC
plc = TemperaturePLC(sender=print_sender)

# • Run it in its own thread so the main program doesn’t block forever
# • Stop after 5 cycles just for demo (≈35 s because INTERVAL = 7 s)
plc_thread = threading.Thread(target=plc.run, kwargs={"cycles": 5}, daemon=True)
plc_thread.start()

# --- keep the main thread alive until the demo is done ---
plc_thread.join()
print("Demo finished.")
