# qwen3-tts-audiobook

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

Voice cloning toolkit for audiobooks and podcasts using Qwen3-TTS. Clone your voice in multiple emotional tones, convert markdown to audio, and generate multi-speaker content.

## Features

- **Voice Cloning** - Clone any voice from a 20-30 second audio sample
- **Markdown to Audio** - Convert markdown documents to audiobooks
- **Multi-Speaker Podcasts** - Generate dialogues with multiple voice profiles
- **Voice Factory** - Simple tools to prepare and manage voice profiles

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/bluefermion/qwen3-tts-audiobook.git
cd qwen3-tts-audiobook

# Create virtual environment
python3 -m venv venv_qwen3
source venv_qwen3/bin/activate

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install qwen-tts soundfile pydub
```

### 2. Create a Voice Profile

Record yourself speaking for 20-30 seconds, then:

```bash
# Prepare voice from recording
python scripts/voice_factory.py prepare ~/my_recording.mp3 --name my_voice

# Test the voice
python scripts/voice_factory.py test voices/my_voice.wav "Hello, this is a test!"

# Listen to output/test_my_voice.wav
```

### 3. Generate Audio

```bash
# Convert markdown to audio
python scripts/md_to_audio.py document.md --voice my_voice -o audiobook.mp3

# Generate multi-speaker podcast
python scripts/multi_speaker.py script.txt -o podcast.mp3
```

## Scripts

### voice_factory.py - Voice Profile Management

```bash
# Prepare a voice from any audio file
python scripts/voice_factory.py prepare recording.mp3 --name speaker_name

# With transcription for better quality (ICL mode)
python scripts/voice_factory.py prepare recording.mp3 --name speaker_name \
    --transcription "This is exactly what I said in the recording..."

# Test a voice profile
python scripts/voice_factory.py test voices/speaker_name.wav "Test text"

# Clone voice to speak any text
python scripts/voice_factory.py clone voices/speaker_name.wav "Hello world" -o hello.wav

# List all voice profiles
python scripts/voice_factory.py list
```

### md_to_audio.py - Markdown to Audiobook

```bash
# Basic usage
python scripts/md_to_audio.py document.md -o output.mp3

# With specific voice
python scripts/md_to_audio.py document.md --voice my_voice -o output.mp3

# French document
python scripts/md_to_audio.py document_fr.md --language French -o output_fr.mp3
```

### multi_speaker.py - Multi-Speaker Podcasts

Script format:
```
[speaker_name] Text to speak
[speaker_name;instruction] Text with voice instruction (CustomVoice only)
[pause 1s]  # Add a pause
# This is a comment
```

Example script (`podcast_script.txt`):
```
[host_excited] Welcome to the show!

[pause 0.5s]

[guest_warm] Thanks for having me.

[host_serious] Let's dive into today's topic.
```

Generate:
```bash
python scripts/multi_speaker.py podcast_script.txt -o podcast.mp3

# List required voices
python scripts/multi_speaker.py podcast_script.txt --list-voices
```

## Voice Profiles

Voice profiles are stored in the `voices/` directory:

```
voices/
├── my_voice.wav           # Audio file (mono, 24kHz)
├── my_voice.txt           # Optional: transcription for ICL mode
├── my_voice_excited.wav   # Emotional variant
├── my_voice_calm.wav      # Another variant
└── ...
```

### Recording Tips

1. **Duration**: 20-30 seconds works best (not 6!)
2. **Content**: Speak naturally with varied intonation
3. **Environment**: Quiet room, no echo
4. **Format**: The factory converts any format to mono 24kHz WAV

### Two Cloning Modes

| Mode | How to Enable | Quality | Speed |
|------|---------------|---------|-------|
| **x_vector_only** | Just provide WAV file | Good | Fast |
| **ICL** | Add matching .txt transcription | Better | Slower |

For ICL mode, create a `.txt` file with the exact transcription:
```
voices/my_voice.wav   # The audio
voices/my_voice.txt   # Contains: "This is exactly what I said..."
```

## Configuration

### Chunk Size

Default is 4000 characters per chunk (optimized for RTX 3090 24GB). Adjust in scripts:

```python
MAX_CHUNK_CHARS = 4000  # Reduce for smaller GPUs
```

### Pause Durations

In `md_to_audio.py`:
```python
PAUSE_AFTER_TITLE = 1500       # ms after chapter titles
PAUSE_AFTER_SECTION = 1000     # ms after section headers
PAUSE_BETWEEN_PARAGRAPHS = 400 # ms between paragraphs
```

## Models

This toolkit uses Qwen3-TTS models:

| Model | Use Case |
|-------|----------|
| `Qwen3-TTS-12Hz-1.7B-Base` | Clone YOUR voice (default) |
| `Qwen3-TTS-12Hz-1.7B-CustomVoice` | Built-in voices with emotion control |
| `Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Create new voices from descriptions |

## Requirements

- Python 3.10+
- CUDA-capable GPU (tested on RTX 3090 24GB)
- ~8GB VRAM minimum
- ffmpeg (for audio conversion)

## Troubleshooting

### "Temperature too high"

Max temperature is 1.0. Use 0.9 for slight variation:
```bash
python scripts/voice_factory.py clone voice.wav "text" -o out.wav --temperature 0.9
```

### "Voice sounds robotic"

- Use a longer reference recording (20-30s, not 6s)
- Enable ICL mode by adding transcription
- Record with natural varied intonation

### GPU out of memory

Reduce `MAX_CHUNK_CHARS` in the scripts:
```python
MAX_CHUNK_CHARS = 2000  # For 12GB GPUs
MAX_CHUNK_CHARS = 1000  # For 8GB GPUs
```

## Legal & Ethics

### Voice Cloning and Right of Publicity

Voice cloning technology intersects with two distinct legal areas:

1. **Copyright** - Governs the audio recording itself
2. **Right of Publicity** - Protects a person's vocal identity

**Important:** Even if an audio recording is in the public domain, the person's **voice** (their identity) may still be legally protected. Recent legislation (ELVIS Act 2024, California AB 1836) specifically addresses unauthorized AI voice cloning.

### Safe Usage Guidelines

| Use Case | Legal Risk |
|----------|------------|
| Clone **your own voice** | Safe |
| Clone **synthetic voice** (VoiceDesign output) | Safe |
| Clone voice with **explicit consent** | Safe |
| Clone **deceased person** (100+ years) | Generally safe |
| Clone **living person without consent** | **High risk** |

### Demo Voice

The included demo voice (`make demo-voice`) uses Qwen3-TTS-VoiceDesign to create a **100% synthetic voice** with no human likeness. This is legally safe for all uses.

### Disclaimer

**Users are responsible for ensuring they have appropriate rights and consent before cloning any human voice.** This toolkit is provided for legitimate purposes including:
- Personal voice cloning (your own voice)
- Synthetic voice generation
- Consented voice projects
- Research and education

The authors are not liable for misuse of this technology.

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) by Alibaba
- Built with lessons learned the hard way (see [STORY.md](STORY.md))
