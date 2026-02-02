# Multi-Speaker Podcast Guide

Create podcasts and dialogues with multiple speakers using synthetic voices.

## Quick Start

```bash
# 1. Generate two synthetic demo voices
make demo-voices-podcast

# 2. Create your script
cat > my_podcast.txt << 'EOF'
[host] Welcome to the Tech Talk podcast! Today we're exploring
the future of voice synthesis technology.

[pause 0.5s]

[guest] Thanks for having me. It's an exciting time to be
working in this field.

[host] So tell us, what makes the latest generation of
text-to-speech so different from what came before?

[guest] The key breakthrough is zero-shot voice cloning.
With just a few seconds of audio, we can now capture
someone's unique vocal characteristics.

[pause 0.3s]

[host] That sounds both amazing and a little concerning.

[guest] Exactly. The technology is powerful, which is why
we need to be thoughtful about how it's used.

[host] Great point. We'll explore the ethics after this break.

[pause 1s]
EOF

# 3. Generate the podcast
make podcast FILE=my_podcast.txt
```

## Setup: Generate Demo Voices

The demo voices are 100% synthetic (created by VoiceDesign), with no human likeness concerns.

### Automatic Setup

```bash
make demo-voices-podcast
```

This creates two synthetic voices:
- `podcast_host` - Warm, professional narrator voice
- `podcast_guest` - Friendly, conversational voice

### Manual Setup (customize voices)

```bash
# Create custom synthetic voices with VoiceDesign
python scripts/create_synthetic_voice.py \
    --name "my_host" \
    --description "A warm, authoritative male voice with clear diction, suitable for hosting podcasts"

python scripts/create_synthetic_voice.py \
    --name "my_guest" \
    --description "A friendly, enthusiastic female voice with a slight British accent"
```

## Script Format

### Basic Format
```
[speaker_name] Text to speak
```

### With Pauses
```
[speaker_name] First sentence.

[pause 0.5s]

[speaker_name] After a pause.
```

### Comments
```
# This is a comment - ignored by the parser
[host] This line is spoken.
```

### Multi-line Speech
```
[host] This is a long speech that spans
multiple lines. The parser will combine
them into a single segment.

[guest] New speaker starts a new segment.
```

## Complete Example Script

Save as `examples/tech_podcast.txt`:

```
# Tech Talk Podcast - Episode 1: Voice Cloning

[host] Welcome to Tech Talk, the podcast where we explore
the cutting edge of technology. I'm your host.

[pause 0.5s]

[guest] And I'm here as your guide through the fascinating
world of artificial intelligence.

[host] Today's topic is voice cloning. Now, I have to admit,
when I first heard about this technology, I was skeptical.

[guest] That's a common reaction. But the science behind it
is actually quite elegant.

[pause 0.3s]

[host] Walk us through it.

[guest] Essentially, the AI analyzes a short sample of someone's
voice and extracts what we call a speaker embedding. Think of it
as a mathematical fingerprint of their vocal characteristics.

[host] So it's not actually recording and splicing words together?

[guest] Exactly. It's generating entirely new speech that matches
the acoustic properties of the original voice. Pitch, timbre,
speaking rhythm - all captured in that embedding.

[pause 0.5s]

[host] The implications are huge.

[guest] They really are. Audiobook narration, personalized
assistants, accessibility tools, content localization.

[host] But also potential for misuse.

[guest] Which is why responsible development matters so much.
Consent, transparency, and clear attribution are essential.

[pause 0.3s]

[host] Well said. We'll have more on the ethics in our next episode.
Thanks for joining us on Tech Talk!

[guest] Thanks for having me. Until next time!

[pause 1s]
```

## Generate the Podcast

```bash
# Check required voices exist
python scripts/multi_speaker.py examples/tech_podcast.txt --list-voices

# Generate audio
python scripts/multi_speaker.py examples/tech_podcast.txt -o output/tech_podcast.mp3

# Or use make
make podcast FILE=examples/tech_podcast.txt OUT=output/tech_podcast.mp3
```

## Using Your Own Voice

Instead of synthetic voices, record yourself and a friend:

```bash
# Prepare voice profiles (20-30 seconds each)
make prepare FILE=~/host_recording.mp3 NAME=host TRANS="transcription..."
make prepare FILE=~/guest_recording.mp3 NAME=guest TRANS="transcription..."

# Use in script
# [host] Your voice as host
# [guest] Your friend's voice as guest
```

## Advanced: Voice Characteristics

When creating synthetic voices with VoiceDesign, use descriptive prompts:

| Voice Type | Description Prompt |
|------------|-------------------|
| News anchor | "A clear, authoritative voice with measured pacing and neutral accent" |
| Friendly host | "A warm, welcoming voice with natural enthusiasm and conversational tone" |
| Expert guest | "An intelligent, articulate voice that conveys expertise without being condescending" |
| Narrator | "A rich, resonant voice with excellent diction, suitable for audiobooks" |

## Output

Generated podcasts are saved to `output/` directory:
- Format: MP3 (192kbps) or WAV
- Automatic pauses between speakers (400ms default)
- Explicit `[pause Xs]` markers for custom timing

## Troubleshooting

### "Voice not found"
```bash
# List available voices
make voices

# Create missing voice
make demo-voices-podcast
```

### Audio sounds choppy
- Increase pause between segments in script
- Use longer reference audio for voice profiles
- Check GPU memory (reduce MAX_CHUNK_CHARS if needed)

### Voices sound too similar
- Use more distinct voice descriptions for VoiceDesign
- Record different people for authentic variety
