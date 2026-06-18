import os
import wave
import struct
import math

def generate_test_wav(filepath, duration=8, sample_rate=44100):
    # Generates a simple, pleasant synth melody (notes: C4, E4, G4, C5, G4, E4, C4)
    # Frequencies: C4 = 261.63, E4 = 329.63, G4 = 392.00, C5 = 523.25
    melody = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 261.63]
    num_samples = duration * sample_rate
    note_duration = duration / len(melody) # time per note
    
    # Ensure folder exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    print(f"Generating synthesized melody at: {filepath}...")
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(1) # mono
        wav_file.setsampwidth(2) # 16-bit (2 bytes)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = i / sample_rate
            note_idx = int(t / note_duration) % len(melody)
            freq = melody[note_idx]
            
            # Decay envelope for each note to sound like a keyboard/xylophone chime
            note_t = t % note_duration
            envelope = math.exp(-4.0 * note_t) # rapid decay
            
            # Sine wave sound synthesis
            val = math.sin(2 * math.pi * freq * t) * envelope
            
            # Scale to 16-bit range
            sample = int(val * 32767)
            wav_file.writeframesraw(struct.pack('<h', sample))
            
    print("Generation complete! Ready to play.")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    music_path = os.path.join(current_dir, "music", "sample_melody.wav")
    generate_test_wav(music_path)
