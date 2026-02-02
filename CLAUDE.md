# CLAUDE.md - AI Agent Instructions

This file provides context for AI agents (Claude, Gemini, etc.) working on this codebase.

## Project Overview

**qwen3-tts-audiobook** is a voice cloning toolkit built on Alibaba's Qwen3-TTS models. It converts text to speech using cloned or synthetic voices, with support for audiobooks, podcasts, and emotional voice variants.

## Architecture

```
qwen3-tts-audiobook/
├── scripts/                 # Core Python utilities
│   ├── voice_factory.py     # Voice profile management (prepare, test, clone, list)
│   ├── md_to_audio.py       # Markdown → audiobook conversion
│   ├── multi_speaker.py     # Multi-speaker podcast generation
│   ├── create_synthetic_voice.py    # VoiceDesign synthetic voice creation
│   ├── preprocess_for_tts.py        # LLM text preprocessing
│   ├── map_emotions_to_voices.py    # Emotion → voice profile mapping
│   ├── transcribe.py        # Whisper audio-to-text transcription
│   └── validate_audio.py    # Quality validation (stuttering detection)
├── tts_ui.py                # Terminal UI (Textual framework)
├── Makefile                 # Build automation (primary interface)
├── voices/                  # Voice profiles (.wav + optional .txt transcriptions)
├── output/                  # Generated audio files
├── examples/                # Sample markdown and podcast scripts
└── docs/                    # Advanced guides (AUDIOBOOK.md, EMOTION.md, PODCAST.md)
```

## Key Technical Details

### Qwen3-TTS Models

| Model | Purpose |
|-------|---------|
| `Qwen3-TTS-12Hz-1.7B-Base` | Clone real voices (requires audio sample) |
| `Qwen3-TTS-12Hz-1.7B-CustomVoice` | Built-in voices with emotion/instruction control |
| `Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Generate synthetic voices from text descriptions |

### Voice Cloning Modes

- **x_vector_only**: Fast, good quality. Just provide a .wav file.
- **ICL (In-Context Learning)**: Better quality. Requires .wav + matching .txt transcription.

### Critical Constraints

- **Temperature**: Max 1.0 (not 1.2-1.5 as some docs claim). Use 0.9 for variety.
- **Recording duration**: 20-30 seconds (not 6 seconds).
- **Audio format**: Mono, 24kHz WAV (voice_factory.py handles conversion).
- **Chunk size**: 4000 chars for 24GB VRAM, reduce for smaller GPUs.

### Pause Timing (ms)

```python
PAUSE_AFTER_TITLE = 1500        # Chapter titles
PAUSE_AFTER_SECTION = 1000      # Section headers
PAUSE_AFTER_SUBSECTION = 700    # Subsections
PAUSE_BETWEEN_PARAGRAPHS = 400  # Paragraphs
PAUSE_BETWEEN_CHUNKS = 300      # Audio chunks
```

## Development Commands

```bash
make install          # Set up environment
make check            # Verify GPU, dependencies
make demo-voice       # Create synthetic test voice
make test VOICE=name  # Test a voice profile
make convert FILE=x   # Convert markdown to audio
make podcast FILE=x   # Generate multi-speaker podcast
make audiobook FILE=x # Full pipeline (LLM + emotions + TTS)
make transcribe FILE=x # Transcribe audio to text (Whisper)
make validate FILE=x  # Validate audio quality (detect stuttering)
make ui               # Launch terminal UI
```

## Quality Validation Workflow

For detecting stuttering or quality issues in generated audio:

```bash
# 1. Generate audio
make convert FILE=document.md VOICE=my_voice

# 2. Transcribe to check what was actually said
make transcribe FILE=output/document.mp3

# 3. Validate for stuttering/repetition
make validate FILE=output/document.mp3

# 4. Validate against expected text
make validate FILE=output/chunk.wav EXPECTED="This is what it should say"
```

The validation script detects:
- **Stuttering**: Repeated words ("the the the") or syllables ("I-I-I")
- **Repetition**: Repeated phrases ("I want to I want to")
- **Gibberish**: Nonsense characters or very long words
- **Incomplete**: Sentences cut off mid-word

## Code Patterns

### Adding a New Script

1. Place in `scripts/` directory
2. Use argparse for CLI interface
3. Add corresponding Makefile target
4. Update README.md Scripts section

### Voice Profile Format

```
voices/
├── speaker_name.wav      # Audio (mono 24kHz, required)
└── speaker_name.txt      # Transcription (optional, enables ICL mode)
```

### Multi-Speaker Script Format

```
[speaker_name] Text to speak
[speaker_name;instruction] Text with emotion instruction
[pause 1.5s] Pause for 1.5 seconds
# This is a comment
```

## External Dependencies

- **Demeterics API**: Used by `preprocess_for_tts.py` for LLM text preprocessing. Requires `DEMETERICS_API_KEY` in `.env`. See [demeterics.ai/docs/api-reference](https://demeterics.ai/docs/api-reference).
- **OpenAI Whisper**: Used by `transcribe.py` and `validate_audio.py` for local audio transcription.
- **ffmpeg**: Required for audio format conversion.
- **CUDA**: GPU acceleration required (8GB+ VRAM).

## Testing Changes

1. Run `make check` to verify environment
2. Create a synthetic voice: `make demo-voice`
3. Test with: `make test VOICE=synthetic_narrator`
4. Try markdown conversion: `make convert FILE=examples/english/sample.md VOICE=synthetic_narrator`

## Legal Context

Voice cloning involves Right of Publicity concerns. The toolkit emphasizes:
- Cloning your own voice (safe)
- Synthetic voices via VoiceDesign (safe)
- Explicit consent for others' voices

See README.md Legal & Ethics section for details.
