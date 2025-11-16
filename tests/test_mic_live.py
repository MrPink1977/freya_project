import sounddevice as sd
import numpy as np
import time

CHUNK = 1024
CHANNELS = 1
RATE = 16000
SAMPLE_DURATION = 5  # seconds

print("Opening microphone... will check levels every 5 seconds")
print("Press Ctrl+C to stop\n")

try:
    sample_count = 1
    while True:
        print(f"Sample #{sample_count} - Recording for {SAMPLE_DURATION} seconds... SPEAK NOW!")
        
        # Record audio using sounddevice
        audio_data = sd.rec(
            int(SAMPLE_DURATION * RATE),
            samplerate=RATE,
            channels=CHANNELS,
            dtype='int16'
        )
        sd.wait()  # Wait until recording is finished
        
        # Flatten the audio data
        audio_data = audio_data.flatten()
        
        # Calculate average and peak volume
        if len(audio_data) > 0:
            avg_volume = int(np.sqrt(np.mean(np.abs(audio_data)**2)))
            peak_volume = int(np.max(np.abs(audio_data)))
            
            # Visual bar for average
            bar_length = min(avg_volume // 50, 50)
            bar = "█" * bar_length
            
            print(f"  Average: {avg_volume:5d} | Peak: {peak_volume:5d} | {bar}")
            
            # Give feedback
            if avg_volume < 500:
                print("  ⚠️  Very quiet - speak louder or increase mic volume!")
            elif avg_volume < 1000:
                print("  ⚡ Good level - should work fine")
            else:
                print("  🔊 Strong signal - excellent!")
        else:
            print("  No audio data captured")
        
        print()  # Blank line
        sample_count += 1
        time.sleep(1)  # Small pause between samples

except KeyboardInterrupt:
    print("\n\n✓ Stopped!")