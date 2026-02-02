# Audiobook Production Guide

Create professional audiobooks with expressive narration using LLM-assisted preprocessing and emotional voice variants.

## Overview

The audiobook workflow:

```
Markdown → LLM Preprocessing → Emotional Tagging → TTS Generation → MP3
```

1. **LLM Preprocessing**: Clean text, fix pronunciation, add pauses
2. **Emotional Analysis**: LLM suggests tone for each segment
3. **Voice Mapping**: Map emotions to your voice variants
4. **Generation**: Produce final audio with natural dynamics

## Quick Start

```bash
# 1. Setup emotional voice variants
make demo-voices-emotion

# 2. Preprocess with LLM (adds emotional tags)
python scripts/preprocess_for_tts.py chapter1.md --with-instructions -o chapter1_speech.txt

# 3. Convert emotional tags to voice variants
python scripts/map_emotions_to_voices.py chapter1_speech.txt -o chapter1_podcast.txt

# 4. Generate audio
make podcast FILE=chapter1_podcast.txt OUT=audiobook/chapter1.mp3
```

## Step 1: Prepare Your Voice Variants

Record yourself in 3-5 emotional states for natural narration dynamics.

### Recommended Variants for Audiobooks

| Variant | Use For | Recording Tip |
|---------|---------|---------------|
| `narrator_calm` | Explanations, descriptions | Relaxed, even pace |
| `narrator_warm` | Dialogue, friendly passages | Smile while speaking |
| `narrator_serious` | Warnings, important facts | Lower register, measured |
| `narrator_excited` | Reveals, climaxes | Higher energy, faster |
| `narrator_reflective` | Philosophical passages | Slower, thoughtful pauses |

### Setup with Your Voice

```bash
# Record each emotion (20-30 seconds, same text for consistency)
RECORDING_TEXT="When we think about the future of civilization, we must consider how technology reshapes human potential. The abundance of energy, intelligence, and automation creates possibilities our ancestors could never imagine."

# Prepare each variant
make prepare FILE=~/calm_recording.mp3 NAME=narrator_calm TRANS="$RECORDING_TEXT"
make prepare FILE=~/warm_recording.mp3 NAME=narrator_warm TRANS="$RECORDING_TEXT"
make prepare FILE=~/serious_recording.mp3 NAME=narrator_serious TRANS="$RECORDING_TEXT"
make prepare FILE=~/excited_recording.mp3 NAME=narrator_excited TRANS="$RECORDING_TEXT"
```

### Or Use Synthetic Demo Voices

```bash
make demo-voices-emotion
```

## Step 2: LLM Preprocessing

The LLM cleans up text and adds emotional guidance.

### Basic Preprocessing (no emotions)

```bash
python scripts/preprocess_for_tts.py chapter.md -o chapter_speech.txt
```

**What it does:**
- Expands abbreviations: `AI` → `A.I.`, `etc.` → `etcetera`
- Adds pauses: `[pause 1s]` after headers, `[pause 0.5s]` between paragraphs
- Removes markdown artifacts
- Converts numbers: `90/10` → `ninety-ten`

### With Emotional Instructions

```bash
python scripts/preprocess_for_tts.py chapter.md --with-instructions -o chapter_speech.txt
```

**Output example:**
```
[warm and engaging] Welcome to chapter three, where we explore the foundations
of post-scarcity economics.

[pause 1s]

[calm and measured] The traditional economic model assumes scarcity as a
fundamental constraint. Resources are limited, and competition determines
their allocation.

[pause 0.5s]

[serious and thoughtful] But what happens when that assumption no longer holds?

[excited and revelatory] This is where everything changes! When energy becomes
essentially free, when A.I. can perform most cognitive tasks, the rules we've
lived by for millennia begin to dissolve.

[pause 0.3s]

[reflective] The question isn't whether abundance is coming. It's whether
we'll be ready for it.
```

## Step 3: Map Emotions to Voice Variants

Convert LLM emotional tags to your actual voice profile names.

### Create Mapping Script

Save as `scripts/map_emotions_to_voices.py`:

```python
#!/usr/bin/env python3
"""Map emotional instruction tags to voice profile names."""

import re
import sys
from pathlib import Path

# Emotion to voice mapping
EMOTION_MAP = {
    # Warm/friendly emotions
    "warm": "narrator_warm",
    "friendly": "narrator_warm",
    "welcoming": "narrator_warm",
    "engaging": "narrator_warm",

    # Calm/neutral emotions
    "calm": "narrator_calm",
    "measured": "narrator_calm",
    "neutral": "narrator_calm",
    "explanatory": "narrator_calm",

    # Serious/authoritative emotions
    "serious": "narrator_serious",
    "thoughtful": "narrator_serious",
    "grave": "narrator_serious",
    "authoritative": "narrator_serious",
    "important": "narrator_serious",

    # Excited/energetic emotions
    "excited": "narrator_excited",
    "enthusiastic": "narrator_excited",
    "revelatory": "narrator_excited",
    "energetic": "narrator_excited",
    "passionate": "narrator_excited",

    # Reflective/philosophical emotions
    "reflective": "narrator_calm",  # or create narrator_reflective
    "philosophical": "narrator_calm",
    "contemplative": "narrator_calm",
}

DEFAULT_VOICE = "narrator_calm"

def map_instruction_to_voice(instruction: str) -> str:
    """Map an instruction tag to a voice profile."""
    instruction_lower = instruction.lower()

    for emotion, voice in EMOTION_MAP.items():
        if emotion in instruction_lower:
            return voice

    return DEFAULT_VOICE

def process_file(input_path: str, output_path: str):
    """Process a speech file and map instructions to voices."""
    content = Path(input_path).read_text()

    # Pattern: [instruction text] followed by content
    pattern = r'\[([^\]]+)\]\s*'

    def replace_instruction(match):
        instruction = match.group(1)

        # Skip pause commands
        if instruction.lower().startswith("pause"):
            return match.group(0)

        voice = map_instruction_to_voice(instruction)
        return f"[{voice}] "

    result = re.sub(pattern, replace_instruction, content)

    Path(output_path).write_text(result)
    print(f"Mapped: {input_path} -> {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python map_emotions_to_voices.py input.txt [-o output.txt]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "-o" else input_file.replace("_speech.txt", "_podcast.txt")

    process_file(input_file, output_file)
```

### Run the Mapping

```bash
python scripts/map_emotions_to_voices.py chapter1_speech.txt -o chapter1_podcast.txt
```

**Before (LLM output):**
```
[warm and engaging] Welcome to chapter three...
[serious and thoughtful] But what happens when...
[excited and revelatory] This is where everything changes!
```

**After (voice profiles):**
```
[narrator_warm] Welcome to chapter three...
[narrator_serious] But what happens when...
[narrator_excited] This is where everything changes!
```

## Step 4: Generate Audio

```bash
# Generate with multi-speaker script
python scripts/multi_speaker.py chapter1_podcast.txt -o audiobook/chapter1.mp3

# Or use make
make podcast FILE=chapter1_podcast.txt OUT=audiobook/chapter1.mp3
```

## Complete Workflow Script

Save as `scripts/generate_audiobook_chapter.sh`:

```bash
#!/bin/bash
# generate_audiobook_chapter.sh - Full audiobook chapter pipeline

set -e

INPUT_MD="$1"
OUTPUT_MP3="${2:-audiobook/$(basename "$INPUT_MD" .md).mp3}"

if [ -z "$INPUT_MD" ]; then
    echo "Usage: $0 chapter.md [output.mp3]"
    exit 1
fi

BASENAME=$(basename "$INPUT_MD" .md)
SPEECH_FILE="output/audio/${BASENAME}_speech.txt"
PODCAST_FILE="output/audio/${BASENAME}_podcast.txt"

echo "=== Audiobook Generation Pipeline ==="
echo "Input:  $INPUT_MD"
echo "Output: $OUTPUT_MP3"
echo ""

# Step 1: LLM Preprocessing
echo "[1/3] LLM Preprocessing..."
python scripts/preprocess_for_tts.py "$INPUT_MD" --with-instructions -o "$SPEECH_FILE"

# Step 2: Map emotions to voices
echo "[2/3] Mapping emotions to voice profiles..."
python scripts/map_emotions_to_voices.py "$SPEECH_FILE" -o "$PODCAST_FILE"

# Step 3: Generate audio
echo "[3/3] Generating audio..."
python scripts/multi_speaker.py "$PODCAST_FILE" -o "$OUTPUT_MP3"

echo ""
echo "=== Complete ==="
echo "Output: $OUTPUT_MP3"
```

Usage:
```bash
chmod +x scripts/generate_audiobook_chapter.sh
./scripts/generate_audiobook_chapter.sh manuscript/chapter1.md audiobook/chapter1.mp3
```

## Best Practices

### Text Preparation

1. **Clean your markdown first**
   - Remove complex tables (convert to prose)
   - Remove code blocks (or describe them)
   - Remove image references

2. **Add chapter markers**
   ```markdown
   # Chapter 1: The Beginning

   ## Section 1.1: First Steps
   ```

3. **Use natural language**
   - Avoid heavy jargon
   - Write numbers as words for small values

### Emotional Flow

1. **Start warm** - Welcome listeners
2. **Use calm as baseline** - Most content
3. **Serious for key points** - Important warnings/facts
4. **Excited sparingly** - Reveals, breakthroughs
5. **End warm** - Thank listeners, preview next chapter

### Technical Settings

```python
# In scripts, adjust for your hardware:
MAX_CHUNK_CHARS = 4000   # RTX 3090 24GB
MAX_CHUNK_CHARS = 2000   # RTX 3080 12GB
MAX_CHUNK_CHARS = 1000   # RTX 3060 8GB

# Pause durations (ms)
PAUSE_AFTER_CHAPTER = 2000
PAUSE_AFTER_SECTION = 1500
PAUSE_BETWEEN_PARAGRAPHS = 500
PAUSE_EMOTION_TRANSITION = 300
```

## Batch Processing

Generate entire audiobook:

```bash
#!/bin/bash
# generate_full_audiobook.sh

CHAPTERS=(
    "manuscript/preamble.md"
    "manuscript/chapter1.md"
    "manuscript/chapter2.md"
    "manuscript/chapter3.md"
    "manuscript/epilogue.md"
)

mkdir -p audiobook

for chapter in "${CHAPTERS[@]}"; do
    name=$(basename "$chapter" .md)
    echo "Processing: $name"
    ./scripts/generate_audiobook_chapter.sh "$chapter" "audiobook/${name}.mp3"
done

echo "Audiobook complete!"
ls -la audiobook/
```

## Troubleshooting

### LLM adds too many emotion tags
- Edit the system prompt in `preprocess_for_tts.py`
- Add: "Only add emotional tags for significant tone changes, not every paragraph"

### Emotion transitions feel jarring
- Increase pause between emotion changes
- Use `narrator_calm` as a "bridge" between extremes

### Generation is slow
- Reduce MAX_CHUNK_CHARS
- Process chapters in parallel (different terminal windows)
- Use x_vector mode (no ICL) for faster generation

### Audio quality issues
- Use longer voice reference recordings (30s ideal)
- Enable ICL mode (add .txt transcription files)
- Check GPU memory usage during generation
