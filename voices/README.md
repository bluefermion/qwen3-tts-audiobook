# Voice Profiles

This directory stores voice profiles for TTS generation.

## Creating a Voice Profile

### Option 1: Using voice_factory.py (Recommended)

```bash
# Basic preparation (converts to mono 24kHz WAV)
python scripts/voice_factory.py prepare ~/recording.mp3 --name my_voice

# With transcription for ICL mode (better quality)
python scripts/voice_factory.py prepare ~/recording.mp3 --name my_voice \
    --transcription "This is exactly what I said in the recording..."

# Test the voice
python scripts/voice_factory.py test voices/my_voice.wav "Hello, this is a test!"
```

### Option 2: Manual Preparation

1. **Record audio**: 20-30 seconds of natural speech
2. **Convert to proper format**:
   ```bash
   ffmpeg -i recording.mp3 -ac 1 -ar 24000 -acodec pcm_s16le voices/my_voice.wav
   ```
3. **(Optional) Add transcription** for ICL mode:
   ```bash
   echo "Exact transcription of what you said..." > voices/my_voice.txt
   ```

## File Structure

```
voices/
├── speaker_name.wav       # Required: mono 24kHz PCM WAV
├── speaker_name.txt       # Optional: transcription for ICL mode
├── speaker_excited.wav    # Emotional variants
├── speaker_calm.wav
└── ...
```

## Recording Tips

### For Best Results

1. **Duration**: 20-30 seconds (not 6!)
2. **Content**: Natural speech with varied intonation
3. **Environment**: Quiet room, minimal echo
4. **Quality**: Clear audio, no background noise

### What to Say

Read something with varied tone:
- Questions and statements
- Excited and calm parts
- Natural pauses

Example script:
> "When we think about the future of technology, we have to consider both the opportunities and the challenges. What does this mean for society? It means we need to be thoughtful, yet optimistic. The possibilities are truly remarkable."

## Cloning Modes

### x_vector_only Mode (Default)
- Just provide the WAV file
- Extracts voice timbre only
- Fast, good quality

### ICL Mode (Better Prosody)
- Provide WAV + matching TXT transcription
- In-Context Learning uses the transcription
- Slower, better prosody matching

## Emotional Variants

For expressive output, record multiple variants of your voice:

```
voices/
├── narrator_calm.wav       # Relaxed, explanatory tone
├── narrator_excited.wav    # Enthusiastic, energetic
├── narrator_serious.wav    # Measured, thoughtful
└── narrator_warm.wav       # Friendly, conversational
```

Then use them in multi-speaker scripts:
```
[narrator_excited] Welcome to the show!
[narrator_serious] Now let's discuss the serious implications.
[narrator_calm] Here's how this works in practice...
```

## Privacy Note

Voice files are personal biometric data. The `.gitignore` excludes:
- `voices/*.wav`
- `voices/*.mp3`
- `voices/*.txt`

Only this README is tracked in git.
