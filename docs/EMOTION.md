# Emotional Voice Variants Guide

Create expressive audio using a single identity with multiple emotional tones.

## Concept

Instead of one flat voice, record yourself in different emotional states:

```
voices/
├── narrator_calm.wav       # Relaxed, explanatory
├── narrator_excited.wav    # Enthusiastic, energetic
├── narrator_serious.wav    # Measured, thoughtful
└── narrator_warm.wav       # Friendly, conversational
```

Then use them as different "speakers" in your script to add emotional dynamics.

## Quick Start

```bash
# 1. Generate synthetic emotional variants (for demo/testing)
make demo-voices-emotion

# 2. Create an emotional script
cat > emotional_demo.txt << 'EOF'
[narrator_calm] Welcome to this demonstration of emotional voice variants.
We'll explore how the same voice can convey different moods.

[pause 0.5s]

[narrator_excited] And let me tell you, the results are incredible!
You won't believe how natural it sounds!

[pause 0.3s]

[narrator_serious] But we must also consider the implications.
This technology requires responsible use.

[narrator_warm] Thanks for joining us today. We hope you found
this demonstration helpful and inspiring.

[pause 1s]
EOF

# 3. Generate audio
make podcast FILE=emotional_demo.txt
```

## Setup: Synthetic Emotional Voices

For demo/testing, generate synthetic voices with different emotional characteristics:

### Automatic Setup

```bash
make demo-voices-emotion
```

Creates three variants:
- `narrator_calm` - Relaxed, measured pace
- `narrator_excited` - Enthusiastic, higher energy
- `narrator_serious` - Thoughtful, authoritative

### Manual Setup (VoiceDesign)

```bash
# Calm/explanatory
python scripts/create_synthetic_voice.py \
    --name "narrator_calm" \
    --description "A calm, measured male voice with a relaxed pace, suitable for explanations"

# Excited/enthusiastic
python scripts/create_synthetic_voice.py \
    --name "narrator_excited" \
    --description "An enthusiastic, energetic male voice with upbeat intonation and faster pace"

# Serious/authoritative
python scripts/create_synthetic_voice.py \
    --name "narrator_serious" \
    --description "A serious, authoritative male voice with gravitas and measured delivery"
```

## Setup: Your Own Emotional Variants

For the best results, **record yourself** in different emotional states:

### Recording Tips

| Emotion | How to Record |
|---------|---------------|
| **Calm** | Relaxed breathing, slower pace, lower pitch variation |
| **Excited** | Higher energy, faster pace, more pitch variation, smile while speaking |
| **Serious** | Measured pace, lower register, minimal pitch variation |
| **Warm** | Friendly tone, moderate pace, as if talking to a friend |
| **Urgent** | Faster pace, slightly higher pitch, sense of importance |

### Recording Script

Use the same text for all emotions (helps the model capture the difference):

```
"When we think about the future of technology, we see incredible possibilities.
New tools are emerging that will transform how we work, create, and connect.
The question is not whether change will come, but how we'll adapt to it."
```

### Prepare Your Recordings

```bash
# Record each emotion separately (20-30 seconds each)
make prepare FILE=~/narrator_calm.mp3 NAME=narrator_calm \
    TRANS="When we think about the future of technology..."

make prepare FILE=~/narrator_excited.mp3 NAME=narrator_excited \
    TRANS="When we think about the future of technology..."

make prepare FILE=~/narrator_serious.mp3 NAME=narrator_serious \
    TRANS="When we think about the future of technology..."
```

## Script Format

Use emotional variants as different "speakers":

```
[narrator_calm] This is spoken in a calm, measured tone.

[narrator_excited] This is spoken with enthusiasm and energy!

[narrator_serious] This is spoken with gravitas and authority.
```

## Complete Example

Save as `examples/product_launch.txt`:

```
# Product Launch Announcement

[narrator_warm] Hello everyone, and thank you for joining us today.

[pause 0.5s]

[narrator_calm] We've been working on something special for the past
two years. Today, we're finally ready to share it with you.

[pause 0.3s]

[narrator_excited] Introducing the next generation of voice synthesis!
This is the breakthrough we've all been waiting for!

[narrator_calm] Let me walk you through the key features.

[pause 0.3s]

[narrator_calm] First, zero-shot voice cloning. With just thirty seconds
of audio, you can create a high-quality voice profile.

[narrator_calm] Second, multi-language support. The same voice can speak
English, French, Chinese, Japanese, and Korean.

[narrator_excited] And third - this is the big one - real-time generation!
No more waiting for audio to render!

[pause 0.5s]

[narrator_serious] Now, we take the ethical implications seriously.
This technology must be used responsibly.

[narrator_serious] We've built in safeguards and require explicit consent
for any voice cloning of real individuals.

[pause 0.3s]

[narrator_warm] We're excited to see what you'll create.
Thank you for being part of this journey.

[pause 1s]
```

## When to Use Each Emotion

| Content Type | Recommended Emotion |
|--------------|---------------------|
| Explanations, tutorials | `calm` |
| Announcements, reveals | `excited` |
| Warnings, important info | `serious` |
| Welcomes, closings | `warm` |
| Call to action | `excited` or `urgent` |
| Statistics, data | `serious` or `calm` |
| Stories, anecdotes | `warm` |

## Generate Audio

```bash
# Check voices
make voices

# Generate
python scripts/multi_speaker.py examples/product_launch.txt -o output/product_launch.mp3

# Or
make podcast FILE=examples/product_launch.txt
```

## Combining with LLM Preprocessing

For longer documents, use the LLM to suggest emotional tags:

```bash
# Preprocess with emotional instructions
python scripts/preprocess_for_tts.py document.md --with-instructions -o document_speech.txt

# The LLM will add tags like:
# [warm and engaging] Welcome to...
# [serious and measured] The data shows...
# [excited] This is a breakthrough!
```

Then map the instruction tags to your voice variants in the script.

## Troubleshooting

### Emotions sound too similar
- Record with more exaggerated emotions (the model will smooth them)
- Use longer reference recordings
- Try different voice descriptions for VoiceDesign

### Transitions feel jarring
- Add `[pause 0.3s]` between emotion changes
- Use transitional phrases in your script
- Consider using `calm` as your baseline and only switching for emphasis
