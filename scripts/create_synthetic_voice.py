#!/usr/bin/env python3
"""
create_synthetic_voice.py - Create a synthetic voice using VoiceDesign

Generates a 100% AI voice from a text description - no human likeness involved.
Legally safe for any use.

Usage:
    python scripts/create_synthetic_voice.py --name my_voice \
        --description "A warm, friendly male voice with clear diction"

    python scripts/create_synthetic_voice.py --name narrator_excited \
        --description "An enthusiastic, energetic voice with upbeat intonation"
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VOICES_DIR = PROJECT_ROOT / "voices"
VENV_PYTHON = PROJECT_ROOT / "venv_qwen3" / "bin" / "python"

# Sample text for voice generation (demonstrates the voice characteristics)
DEFAULT_SAMPLE_TEXT = """
Welcome to the voice synthesis demonstration. This voice was generated
entirely by artificial intelligence, using only a text description.
The technology captures tone, pace, and character from natural language prompts.
"""


def create_voice(name: str, description: str, sample_text: str = None):
    """Create a synthetic voice using VoiceDesign."""
    import subprocess

    if sample_text is None:
        sample_text = DEFAULT_SAMPLE_TEXT.strip()

    VOICES_DIR.mkdir(parents=True, exist_ok=True)

    script = f'''
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

print("Loading Qwen3-TTS-VoiceDesign...")
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0" if torch.cuda.is_available() else "cpu",
    dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
)

voice_desc = """{description}"""
sample_text = """{sample_text}"""

print(f"Generating voice: {{voice_desc[:60]}}...")
wavs, sr = model.generate_voice_design(
    text=sample_text,
    language="English",
    instruct=voice_desc,  # instruct is the voice description parameter
)

output_path = "{VOICES_DIR / f'{name}.wav'}"
sf.write(output_path, wavs[0], sr)

# Save transcription for ICL mode
trans_path = "{VOICES_DIR / f'{name}.txt'}"
with open(trans_path, "w") as f:
    f.write(sample_text)

duration = len(wavs[0]) / sr
print(f"Created: {{output_path}}")
print(f"Duration: {{duration:.1f}}s")
print(f"Transcription: {{trans_path}}")
'''

    result = subprocess.run(
        [str(VENV_PYTHON), "-c", script],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create a synthetic voice using VoiceDesign"
    )
    parser.add_argument("--name", "-n", required=True, help="Voice profile name")
    parser.add_argument("--description", "-d", required=True,
                        help="Voice description (e.g., 'A warm, friendly male voice')")
    parser.add_argument("--sample-text", "-t",
                        help="Sample text for voice generation (default: demo text)")

    args = parser.parse_args()

    print("=" * 50)
    print("Synthetic Voice Creation")
    print("=" * 50)
    print(f"Name: {args.name}")
    print(f"Description: {args.description}")
    print()

    success = create_voice(args.name, args.description, args.sample_text)

    if success:
        print()
        print("=" * 50)
        print("Voice created successfully!")
        print("=" * 50)
        print(f"Test with: make test VOICE={args.name}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
