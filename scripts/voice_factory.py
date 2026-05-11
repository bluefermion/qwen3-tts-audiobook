#!/usr/bin/env python3
"""
voice_factory.py - Simple voice cloning factory

Create voice profiles from raw recordings. This is the "factory" that takes
your raw recordings and produces ready-to-use voice profiles.

Usage:
    # Prepare a single voice (convert to proper format)
    python scripts/voice_factory.py prepare recording.mp3 --name my_voice

    # Test a voice profile
    python scripts/voice_factory.py test voices/my_voice.wav "This is exciting!"

    # Clone text with a voice profile
    python scripts/voice_factory.py clone voices/my_voice.wav "Hello world" -o output.wav

    # List all voice profiles
    python scripts/voice_factory.py list

    # Create voice profile with transcription (for ICL mode)
    python scripts/voice_factory.py prepare recording.mp3 --name narrator_calm \
        --transcription "This is what I said in the recording..."

Voice Profile Format:
    voices/
    ├── narrator_calm.wav           # Audio file (mono, 24kHz)
    ├── narrator_calm.txt           # Optional: transcription for ICL mode
    ├── my_voice.wav
    ├── my_voice.txt
    └── ...
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VOICES_DIR = PROJECT_ROOT / "voices"
OUTPUT_DIR = PROJECT_ROOT / "output"
VENV_PYTHON = PROJECT_ROOT / "venv_qwen3" / "bin" / "python"


def prepare_voice(
    input_file: str,
    name: str,
    transcription: Optional[str] = None,
    trim_start: float = 0,
    trim_end: float = 0,
    max_duration: float = 30,
) -> Path:
    """
    Prepare a voice recording for use as a profile.

    Converts to mono 24kHz WAV format optimal for Qwen3-TTS.

    Args:
        input_file: Path to raw recording (any format ffmpeg supports)
        name: Profile name (e.g., "my_voice")
        transcription: Optional exact transcription for ICL mode
        trim_start: Seconds to trim from start
        trim_end: Seconds to trim from end (0 = no trim)
        max_duration: Maximum duration in seconds

    Returns:
        Path to the prepared voice file
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = VOICES_DIR / f"{name}.wav"

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    # Trim options
    if trim_start > 0:
        cmd.extend(["-ss", str(trim_start)])
    if trim_end > 0:
        cmd.extend(["-to", str(trim_end)])
    elif max_duration > 0:
        cmd.extend(["-t", str(max_duration)])

    # Convert to mono 24kHz PCM
    cmd.extend([
        "-ac", "1",              # Mono
        "-ar", "24000",          # 24kHz sample rate
        "-acodec", "pcm_s16le",  # 16-bit PCM
        str(output_path)
    ])

    print(f"Converting: {input_path.name} -> {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Audio conversion failed")

    # Save transcription if provided
    if transcription:
        trans_path = VOICES_DIR / f"{name}.txt"
        trans_path.write_text(transcription.strip(), encoding="utf-8")
        print(f"Saved transcription: {trans_path.name}")

    # Get audio info
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(output_path)
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    if probe_result.returncode == 0:
        info = json.loads(probe_result.stdout)
        duration = float(info.get("format", {}).get("duration", 0))
        print(f"Duration: {duration:.1f}s")

    print(f"Voice profile ready: {output_path}")
    return output_path


def test_voice(voice_file: str, text: str, output: Optional[str] = None) -> Path:
    """
    Test a voice profile by generating a short sample.

    Args:
        voice_file: Path to voice profile WAV
        text: Text to synthesize
        output: Optional output path (default: output/test_<voice>.wav)

    Returns:
        Path to generated audio
    """
    voice_path = Path(voice_file)
    if not voice_path.exists():
        raise FileNotFoundError(f"Voice file not found: {voice_file}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output:
        output_path = Path(output)
    else:
        output_path = OUTPUT_DIR / f"test_{voice_path.stem}.wav"

    # Check for transcription file (ICL mode)
    trans_path = voice_path.with_suffix(".txt")
    use_icl = trans_path.exists()

    print(f"Voice: {voice_path.name}")
    print(f"Mode: {'ICL (with transcription)' if use_icl else 'x_vector_only'}")
    print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")

    # Generate using a fixed inline helper that reads user-supplied text
    # from stdin as JSON. The previous implementation f-string-interpolated
    # `text` and `trans_text` directly into a Python source string with
    # `"""..."""` quoting; any triple-quote (or backslash) in a transcription
    # file would escape the literal and execute as Python.
    payload = {
        "ref_audio": str(voice_path),
        "output_path": str(output_path),
        "text": text,
    }
    if use_icl:
        payload["ref_text"] = trans_path.read_text(encoding="utf-8").strip()

    script = '''
import json, sys, torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

data = json.loads(sys.stdin.read())
ref_audio = data["ref_audio"]
output_path = data["output_path"]
text = data["text"]
ref_text = data.get("ref_text")

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

if ref_text is not None:
    wavs, sr = model.generate_voice_clone(
        text=text, language="English",
        ref_audio=ref_audio, ref_text=ref_text,
    )
else:
    wavs, sr = model.generate_voice_clone(
        text=text, language="English",
        ref_audio=ref_audio, x_vector_only_mode=True,
    )

sf.write(output_path, wavs[0], sr)
print(f"Generated: {output_path}")
print(f"Duration: {len(wavs[0])/sr:.1f}s")
'''

    result = subprocess.run(
        [str(VENV_PYTHON), "-c", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Voice test failed")

    print(result.stdout)
    return output_path


def clone_voice(
    voice_file: str,
    text: str,
    output: str,
    language: str = "English",
    temperature: float = 1.0,
) -> Path:
    """
    Clone a voice to speak given text.

    Args:
        voice_file: Path to voice profile WAV
        text: Text to synthesize
        output: Output file path
        language: Language for TTS
        temperature: Sampling temperature (0.9-1.0)

    Returns:
        Path to generated audio
    """
    voice_path = Path(voice_file)
    if not voice_path.exists():
        raise FileNotFoundError(f"Voice file not found: {voice_file}")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for transcription file
    trans_path = voice_path.with_suffix(".txt")
    use_icl = trans_path.exists()

    print(f"Cloning voice: {voice_path.name}")
    print(f"Language: {language}")
    print(f"Output: {output_path}")

    # Build payload (see test_voice above for why interpolation is avoided).
    payload = {
        "ref_audio": str(voice_path),
        "output_path": str(output_path),
        "text": text,
        "language": language,
        "temperature": temperature,
    }
    if use_icl:
        payload["ref_text"] = trans_path.read_text(encoding="utf-8").strip()

    script = '''
import json, sys, torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

data = json.loads(sys.stdin.read())
ref_audio = data["ref_audio"]
output_path = data["output_path"]
text = data["text"]
language = data["language"]
temperature = data["temperature"]
ref_text = data.get("ref_text")

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

gen_kwargs = {}
if temperature != 1.0:
    gen_kwargs["temperature"] = temperature
    gen_kwargs["do_sample"] = True

if ref_text is not None:
    wavs, sr = model.generate_voice_clone(
        text=text, language=language,
        ref_audio=ref_audio, ref_text=ref_text,
        **gen_kwargs,
    )
else:
    wavs, sr = model.generate_voice_clone(
        text=text, language=language,
        ref_audio=ref_audio, x_vector_only_mode=True,
        **gen_kwargs,
    )

sf.write(output_path, wavs[0], sr)
print(f"Generated: {output_path}")
print(f"Duration: {len(wavs[0])/sr:.1f}s")
'''

    result = subprocess.run(
        [str(VENV_PYTHON), "-c", script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("Voice cloning failed")

    print(result.stdout)
    return output_path


def list_voices() -> list:
    """List all available voice profiles."""
    if not VOICES_DIR.exists():
        print("No voices directory found.")
        return []

    voices = []
    for wav_file in sorted(VOICES_DIR.glob("*.wav")):
        name = wav_file.stem
        trans_path = wav_file.with_suffix(".txt")
        has_trans = trans_path.exists()

        # Get duration
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(wav_file)
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = 0
        if probe_result.returncode == 0:
            info = json.loads(probe_result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))

        mode = "ICL" if has_trans else "x_vector"
        voices.append({
            "name": name,
            "file": str(wav_file),
            "duration": duration,
            "mode": mode,
            "has_transcription": has_trans,
        })

        print(f"  {name:20s} {duration:5.1f}s  [{mode}]")

    if not voices:
        print("No voice profiles found in voices/")
        print("\nTo create a voice profile:")
        print("  python scripts/voice_factory.py prepare recording.mp3 --name my_voice")

    return voices


def main():
    parser = argparse.ArgumentParser(
        description="Voice cloning factory - prepare and use voice profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prepare a voice from recording
  python scripts/voice_factory.py prepare ~/recording.mp3 --name my_voice

  # Test a voice profile
  python scripts/voice_factory.py test voices/my_voice.wav "This is exciting!"

  # Clone voice to speak text
  python scripts/voice_factory.py clone voices/my_voice.wav "Hello world" -o hello.wav

  # List all voice profiles
  python scripts/voice_factory.py list
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Prepare command
    prep_parser = subparsers.add_parser("prepare", help="Prepare voice from recording")
    prep_parser.add_argument("input", help="Input audio file")
    prep_parser.add_argument("--name", "-n", required=True, help="Voice profile name")
    prep_parser.add_argument("--transcription", "-t", help="Transcription for ICL mode")
    prep_parser.add_argument("--trim-start", type=float, default=0, help="Trim start (seconds)")
    prep_parser.add_argument("--trim-end", type=float, default=0, help="Trim end (seconds)")
    prep_parser.add_argument("--max-duration", type=float, default=30, help="Max duration (seconds)")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a voice profile")
    test_parser.add_argument("voice", help="Voice profile WAV file")
    test_parser.add_argument("text", help="Text to synthesize")
    test_parser.add_argument("-o", "--output", help="Output file")

    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Clone voice to speak text")
    clone_parser.add_argument("voice", help="Voice profile WAV file")
    clone_parser.add_argument("text", help="Text to synthesize")
    clone_parser.add_argument("-o", "--output", required=True, help="Output file")
    clone_parser.add_argument("-l", "--language", default="English", help="Language")
    clone_parser.add_argument("-t", "--temperature", type=float, default=1.0, help="Temperature")

    # List command
    subparsers.add_parser("list", help="List voice profiles")

    args = parser.parse_args()

    if args.command == "prepare":
        prepare_voice(
            args.input,
            args.name,
            args.transcription,
            args.trim_start,
            args.trim_end,
            args.max_duration,
        )
    elif args.command == "test":
        test_voice(args.voice, args.text, args.output)
    elif args.command == "clone":
        clone_voice(args.voice, args.text, args.output, args.language, args.temperature)
    elif args.command == "list":
        list_voices()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
