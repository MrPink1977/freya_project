import sounddevice as sd
import wave

# Record 5 seconds
CHUNK = 1024
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5

print("Recording for 5 seconds... SPEAK NOW!")

# Record audio using sounddevice
audio_data = sd.rec(
    int(RECORD_SECONDS * RATE),
    samplerate=RATE,
    channels=CHANNELS,
    dtype='int16'
)
sd.wait()  # Wait until recording is finished

print("Done recording!")

# Save to file
wf = wave.open("test_recording.wav", 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(2)  # 16-bit audio
wf.setframerate(RATE)
wf.writeframes(audio_data.tobytes())
wf.close()

print("Saved to test_recording.wav - play it to hear what your mic captured!")