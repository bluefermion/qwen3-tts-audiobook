#!/bin/bash
# setup_demo_voice.sh - Create a synthetic demo voice using Qwen3-TTS-VoiceDesign
#
# This script generates a completely synthetic voice using Qwen3's VoiceDesign model,
# then uses it as a reference for voice cloning. This approach:
#   - Demonstrates the full Qwen3 ecosystem (VoiceDesign -> Clone)
#   - Has ZERO human Right of Publicity concerns
#   - Is legally bulletproof for commercial use
#
# The generated voice is 100% synthetic - no human likeness is used.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
VOICES_DIR="$PROJECT_ROOT/voices"
VENV_PYTHON="$PROJECT_ROOT/venv_qwen3/bin/python"

# Demo voice configuration
DEMO_NAME="synthetic_narrator"
VOICE_DESCRIPTION="A warm, clear male voice with a calm and engaging tone, suitable for narrating audiobooks and educational content."
SAMPLE_TEXT="Welcome to the voice cloning demonstration. This voice was generated entirely by artificial intelligence, with no human likeness involved. The technology you are hearing represents the cutting edge of text-to-speech synthesis."

echo "=========================================="
echo "Synthetic Demo Voice Setup"
echo "=========================================="
echo ""
echo "This creates a 100% synthetic voice using"
echo "Qwen3-TTS-VoiceDesign - no human likeness."
echo ""
echo "Voice description: $VOICE_DESCRIPTION"
echo ""

# Check venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment not found."
    echo "Run: make install"
    exit 1
fi

# Create voices directory
mkdir -p "$VOICES_DIR"

# Generate synthetic voice
echo "Generating synthetic voice profile..."

$VENV_PYTHON << PYTHON_SCRIPT
import torch
import soundfile as sf
from pathlib import Path

try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    print("Error: qwen_tts not installed. Run: pip install qwen-tts")
    exit(1)

VOICES_DIR = Path("$VOICES_DIR")
DEMO_NAME = "$DEMO_NAME"
VOICE_DESC = """$VOICE_DESCRIPTION"""
SAMPLE_TEXT = """$SAMPLE_TEXT"""

print("Loading Qwen3-TTS-VoiceDesign model...")
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    device_map="cuda:0" if torch.cuda.is_available() else "cpu",
    dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
)

print(f"Generating voice from description: {VOICE_DESC[:50]}...")
wavs, sr = model.generate_voice_design(
    text=SAMPLE_TEXT,
    language="English",
    voice_description=VOICE_DESC,
)

output_path = VOICES_DIR / f"{DEMO_NAME}.wav"
sf.write(str(output_path), wavs[0], sr)

# Save transcription for ICL mode
trans_path = VOICES_DIR / f"{DEMO_NAME}.txt"
trans_path.write_text(SAMPLE_TEXT)

duration = len(wavs[0]) / sr
print(f"Generated: {output_path}")
print(f"Duration: {duration:.1f}s")
print(f"Transcription saved for ICL mode")
PYTHON_SCRIPT

echo ""
echo "=========================================="
echo "Synthetic demo voice ready!"
echo "=========================================="
echo ""
echo "Voice profile: voices/${DEMO_NAME}.wav"
echo "Transcription: voices/${DEMO_NAME}.txt"
echo ""
echo "This voice is 100% AI-generated with NO human likeness."
echo "Safe for commercial use - no Right of Publicity concerns."
echo ""
echo "Test it with:"
echo "  make test VOICE=${DEMO_NAME} TEXT=\"Hello, this is a voice cloning test!\""
echo ""
