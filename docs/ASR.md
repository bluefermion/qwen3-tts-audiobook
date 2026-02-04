# Audio Transcription with Qwen3-ASR

This guide covers audio transcription and quality validation using Qwen3-ASR.

## Overview

The toolkit uses **Qwen3-ASR-1.7B** for speech recognition, with **Groq Whisper** (via Demeterics API) as a cloud fallback. This provides:

- Local, fast transcription on your GPU
- Unified Qwen3 ecosystem (TTS + ASR)
- Two-model validation for reliability

## Quick Start

```bash
# Transcribe an audio file
make transcribe FILE=output/podcast.mp3

# Validate audio for quality issues
make validate FILE=output/chunk.wav

# Use Groq cloud backend instead
make transcribe FILE=output/podcast.mp3 BACKEND=groq
```

## Scripts

### transcribe.py

Transcribe audio files to text.

```bash
# Basic transcription
python scripts/transcribe.py output/audio.mp3

# Save to file
python scripts/transcribe.py output/audio.mp3 -o transcript.txt

# With timestamps (requires ForcedAligner)
python scripts/transcribe.py output/audio.mp3 --timestamps -o transcript.json

# Transcribe all files in directory
python scripts/transcribe.py output/ --all -o transcripts.json

# Use Groq backend
python scripts/transcribe.py output/audio.mp3 --backend groq
```

### validate_audio.py

Check audio quality by transcribing and analyzing for issues.

```bash
# Validate single file
python scripts/validate_audio.py output/chunk.wav

# Validate against expected text
python scripts/validate_audio.py output/chunk.wav --expected "Hello world"

# Validate all files in directory
python scripts/validate_audio.py output/ --all

# Generate detailed report
python scripts/validate_audio.py output/podcast.mp3 --report -o report.json

# Strict mode (exit 1 on any issues)
python scripts/validate_audio.py output/chunk.wav --strict
```

## Validation During TTS Generation

When using `--validate` with `md_to_audio.py` or `multi_speaker.py`, the system automatically:

1. Generates audio for each chunk
2. Transcribes the audio using Qwen3-ASR
3. Checks for quality issues (stuttering, repetition, gibberish)
4. Retries up to 5 times if issues are detected

### Two-Model Validation

The retry logic uses two different ASR models for reliability:

| Retry | Backend | Reason |
|-------|---------|--------|
| 1-3 | Qwen3-ASR (local) | Fast, local validation |
| 4-5 | Groq Whisper (cloud) | "Second opinion" from different model |

This helps avoid false positives - if one model consistently flags an issue but another passes it, the audio is likely fine.

### Enable Validation

```bash
# With md_to_audio.py
python scripts/md_to_audio.py document.md --validate -o output.mp3

# With multi_speaker.py
python scripts/multi_speaker.py script.txt --validate -o podcast.mp3

# Via Makefile (enabled by default)
make convert FILE=document.md VOICE=my_voice
make podcast FILE=script.txt
```

## Issues Detected

The validation system checks for:

| Issue | Severity | Description |
|-------|----------|-------------|
| Stuttering | Error | Repeated words ("the the the") |
| Syllable stutter | Error | Repeated syllables ("I-I-I", "wh-wh-what") |
| Phrase repetition | Error | Repeated phrases ("I want to I want to") |
| Gibberish | Error | Very long nonsense words |
| Character repetition | Error | "aaaaaaa" or similar |
| Low similarity | Error | Transcription doesn't match expected text (<50%) |
| Gaps | Warning | Unusual spaces in transcription |
| Incomplete | Warning | Sentences cut off mid-word |

## Backends

### Qwen3-ASR (Default)

Local GPU-based transcription using Alibaba's Qwen3-ASR-1.7B model.

**Pros:**
- Fast (local processing)
- No API costs
- Better Chinese support
- Same ecosystem as Qwen3-TTS

**Cons:**
- Requires GPU (~4GB VRAM)
- First load takes time

### Groq Whisper (Fallback)

Cloud-based transcription via Demeterics API using Groq's `whisper-large-v3-turbo`.

**Pros:**
- No GPU required
- Fast cloud inference
- Different model = second opinion

**Cons:**
- Requires internet
- Requires `DEMETERICS_API_KEY`
- API rate limits

## Configuration

### Environment Variables

```bash
# Required for Groq fallback
DEMETERICS_API_KEY=your_key_here
```

### Models Used

| Component | Model | VRAM |
|-----------|-------|------|
| ASR | Qwen3-ASR-1.7B | ~4GB |
| Timestamps | Qwen3-ForcedAligner-0.6B | ~2GB |

## Programmatic Usage

```python
from scripts.transcribe import transcribe_audio

# Basic transcription
result = transcribe_audio("audio.wav")
print(result["text"])
print(result["language"])

# With Groq backend
result = transcribe_audio("audio.wav", backend="groq")

# With timestamps
result = transcribe_audio("audio.wav", timestamps=True)
for seg in result["segments"]:
    print(f"{seg['start']:.2f}-{seg['end']:.2f}: {seg['text']}")
```

## Performance Benchmarks

Qwen3-ASR vs Whisper (Word Error Rate, lower is better):

| Dataset | Qwen3-ASR-1.7B | Whisper-large-v3 |
|---------|----------------|------------------|
| LibriSpeech clean | 1.63 | 1.51 |
| LibriSpeech other | **3.38** | 3.97 |
| GigaSpeech | **8.45** | 9.76 |
| WenetSpeech (Chinese) | **4.97** | 9.86 |

## Troubleshooting

### "Model not found"

Install qwen-asr:
```bash
pip install qwen-asr
```

### "CUDA out of memory"

The ASR model needs ~4GB VRAM. If running alongside TTS:
- Use smaller TTS chunks
- Use `--backend groq` for cloud transcription

### "Groq transcription unavailable"

Check your `DEMETERICS_API_KEY` environment variable:
```bash
export DEMETERICS_API_KEY=your_key_here
```

### Validation keeps failing

If validation fails repeatedly:
1. Check the audio manually - it might genuinely have issues
2. Try `--backend groq` to get a second opinion
3. Regenerate with a different temperature setting
