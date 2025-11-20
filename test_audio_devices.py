"""List available audio devices."""
import sounddevice as sd

print("Available audio devices:\n")
devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"{i}: {device['name']}")
    if device['max_output_channels'] > 0:
        print(f"   Outputs: {device['max_output_channels']} channels")
    if device['max_input_channels'] > 0:
        print(f"   Inputs: {device['max_input_channels']} channels")
    print()

print(f"\nDefault output device: {sd.default.device[1]}")
print(f"Default output name: {sd.query_devices(sd.default.device[1])['name']}")
