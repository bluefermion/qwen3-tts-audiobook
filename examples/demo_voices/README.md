# Demo Voice Profiles

This directory contains scripts to create demo voices for testing the toolkit.

## Synthetic Voice (Recommended)

The demo voice is generated using **Qwen3-TTS-VoiceDesign** - a model that creates entirely synthetic voices from text descriptions. This approach:

- **100% AI-generated** - no human likeness involved
- **Legally safe** - no Right of Publicity concerns
- **Demonstrates the ecosystem** - shows VoiceDesign → Clone workflow

**Setup:**
```bash
make demo-voice
# or
./examples/demo_voices/setup_demo_voice.sh
```

## Legal Context: Voice Cloning & Right of Publicity

**Important:** Voice cloning technology intersects with two distinct legal areas:

### 1. Copyright (Recording Rights)
- A public domain recording (e.g., LibriVox) can be freely used, edited, and distributed
- This covers the **audio file** itself

### 2. Right of Publicity (Identity Rights)
- A person's **vocal identity** is protected separately from any recording
- Recent laws (ELVIS Act 2024, California AB 1836, New York statutes) specifically address AI voice cloning
- Using someone's voice to generate new speech without consent is legally risky, even if the source recording is public domain

### Safe Approaches for Voice Cloning

| Approach | Legal Risk | Notes |
|----------|------------|-------|
| **Your own voice** | None | You own your identity |
| **Synthetic voice (VoiceDesign)** | None | No human likeness |
| **Consented voice (Mozilla Common Voice)** | Low | Explicit consent for ML use |
| **Pre-1923 recordings (deceased speakers)** | Low | Right of Publicity typically expires 50-100 years after death |
| **Living person without consent** | **High** | Violates Right of Publicity |

### Resources

- [Mozilla Common Voice](https://commonvoice.mozilla.org/) - Consented voice dataset
- [Library of Congress National Jukebox](https://www.loc.gov/collections/national-jukebox/) - Pre-1923 recordings
- [ELVIS Act (Tennessee)](https://www.tn.gov/content/tn/governor/news/2024/3/21/gov--lee-signs-elvis-act-into-law--protecting-tennessee-s-artis.html) - AI voice cloning legislation

## Recording Your Own Voice

For production use, **record your own voice** - it's the safest and most authentic approach.

See the main [README](../../README.md) for recording tips:
- 20-30 seconds of natural speech
- Quiet room, varied intonation
- Save transcription for ICL mode (better quality)
