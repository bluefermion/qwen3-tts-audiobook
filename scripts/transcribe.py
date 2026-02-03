#!/usr/bin/env python3
"""
transcribe.py - Transcribe audio files using Qwen3-ASR (with Groq fallback)

Converts audio files (mp3, wav, etc.) to text using the Qwen3-ASR model.
Useful for quality validation of TTS output and creating transcriptions for ICL mode.

Usage:
    # Transcribe a single file
    python scripts/transcribe.py output/audiobook.mp3

    # Transcribe with timestamps (requires ForcedAligner)
    python scripts/transcribe.py output/audiobook.mp3 --timestamps

    # Output to file instead of stdout
    python scripts/transcribe.py output/audiobook.mp3 -o transcription.txt

    # Transcribe all files in a directory
    python scripts/transcribe.py output/ --all

    # Use Groq/Demeterics API instead of local model
    python scripts/transcribe.py output/chunk.wav --backend groq

Backends:
    qwen   - Local Qwen3-ASR-1.7B model (default, requires GPU)
    groq   - Groq's Whisper via Demeterics API (requires DEMETERICS_API_KEY)

Requires:
    pip install qwen-asr
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

# Cached model instance (for repeated calls)
_qwen_model = None


def transcribe_qwen(
    audio_file: str,
    language: Optional[str] = None,
    timestamps: bool = False,
) -> dict:
    """
    Transcribe audio file using Qwen3-ASR.

    Args:
        audio_file: Path to audio file
        language: Language hint (e.g., "English", "Chinese") or None for auto-detect
        timestamps: Whether to include word-level timestamps (requires ForcedAligner)

    Returns:
        Dictionary with transcription results
    """
    global _qwen_model

    import torch
    from qwen_asr import Qwen3ASRModel

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # Load model (cached)
    if _qwen_model is None:
        print("Loading Qwen3-ASR model...")
        model_kwargs = {
            "dtype": torch.bfloat16,
            "device_map": "cuda:0",
            "max_inference_batch_size": 32,
            "max_new_tokens": 256,
        }

        # Add forced aligner for timestamps
        if timestamps:
            model_kwargs["forced_aligner"] = "Qwen/Qwen3-ForcedAligner-0.6B"
            model_kwargs["forced_aligner_kwargs"] = {
                "dtype": torch.bfloat16,
                "device_map": "cuda:0",
            }

        _qwen_model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            **model_kwargs
        )

    print(f"Transcribing: {audio_path.name}")

    # Transcribe
    results = _qwen_model.transcribe(
        audio=str(audio_path),
        language=language,
        return_time_stamps=timestamps,
    )

    result = results[0]

    output = {
        "file": str(audio_path),
        "text": result.text.strip(),
        "language": result.language,
    }

    if timestamps and hasattr(result, "time_stamps") and result.time_stamps:
        output["segments"] = [
            {
                "text": ts.text,
                "start": ts.start_time,
                "end": ts.end_time,
            }
            for ts in result.time_stamps
        ]
        if result.time_stamps:
            output["duration"] = result.time_stamps[-1].end_time

    return output


def transcribe_groq(audio_file: str) -> dict:
    """
    Transcribe audio using Groq's Whisper API via Demeterics.

    Requires DEMETERICS_API_KEY environment variable.

    Args:
        audio_file: Path to audio file

    Returns:
        Dictionary with transcription results
    """
    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    api_key = os.environ.get("DEMETERICS_API_KEY")
    if not api_key:
        raise ValueError("DEMETERICS_API_KEY environment variable not set")

    print(f"Transcribing via Groq: {audio_path.name}")

    result = subprocess.run(
        [
            "curl", "-s",
            "-X", "POST",
            "https://api.demeterics.com/groq/v1/audio/transcriptions",
            "-H", f"Authorization: Bearer {api_key}",
            "-F", f"file=@{audio_path}",
            "-F", "model=whisper-large-v3-turbo",
            "-F", "response_format=verbose_json",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Groq API call failed: {result.stderr}")

    data = json.loads(result.stdout)

    if "error" in data:
        raise RuntimeError(f"Groq API error: {data['error']}")

    output = {
        "file": str(audio_path),
        "text": data.get("text", "").strip(),
        "language": data.get("language", ""),
    }

    # Include segments if available
    if "segments" in data:
        output["segments"] = [
            {
                "text": seg.get("text", "").strip(),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
            }
            for seg in data["segments"]
        ]
        if data["segments"]:
            output["duration"] = data["segments"][-1].get("end", 0)

    return output


def transcribe_audio(
    audio_file: str,
    backend: str = "qwen",
    language: Optional[str] = None,
    timestamps: bool = False,
) -> dict:
    """
    Transcribe audio file using specified backend.

    Args:
        audio_file: Path to audio file
        backend: "qwen" (local) or "groq" (cloud)
        language: Language hint or None for auto-detect
        timestamps: Whether to include word-level timestamps

    Returns:
        Dictionary with transcription results:
            - file: Path to audio file
            - text: Transcribed text
            - language: Detected language
            - segments: List of timestamped segments (if timestamps=True)
            - duration: Audio duration in seconds (if available)
    """
    if backend == "groq":
        return transcribe_groq(audio_file)
    else:
        return transcribe_qwen(audio_file, language, timestamps)


def format_output(result: dict, timestamps: bool = False) -> str:
    """Format transcription result for display."""
    if timestamps:
        return json.dumps(result, indent=2, ensure_ascii=False)
    else:
        return result["text"]


def transcribe_directory(
    directory: str,
    backend: str = "qwen",
    language: Optional[str] = None,
    extensions: tuple = (".wav", ".mp3", ".m4a", ".flac", ".ogg"),
) -> list:
    """Transcribe all audio files in a directory."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    audio_files = []
    for ext in extensions:
        audio_files.extend(dir_path.glob(f"*{ext}"))

    audio_files = sorted(audio_files)
    if not audio_files:
        print(f"No audio files found in {directory}")
        return []

    print(f"Found {len(audio_files)} audio files")
    results = []

    for audio_file in audio_files:
        try:
            result = transcribe_audio(str(audio_file), backend, language)
            results.append(result)
            print(f"  {audio_file.name}: {len(result['text'])} chars")
        except Exception as e:
            print(f"  {audio_file.name}: ERROR - {e}")
            results.append({
                "file": str(audio_file),
                "error": str(e),
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using Qwen3-ASR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/transcribe.py output/test.wav
  python scripts/transcribe.py output/podcast.mp3 --timestamps
  python scripts/transcribe.py output/chunk.wav -o chunk.json
  python scripts/transcribe.py output/ --all -o transcriptions.json
  python scripts/transcribe.py output/test.wav --backend groq
        """
    )

    parser.add_argument("input", help="Audio file or directory")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--backend", "-b",
        default="qwen",
        choices=["qwen", "groq"],
        help="Transcription backend (default: qwen)"
    )
    parser.add_argument(
        "--language", "-l",
        help="Language hint (e.g., 'English', 'Chinese'). Auto-detect if not specified."
    )
    parser.add_argument(
        "--timestamps", "-t",
        action="store_true",
        help="Include word-level timestamps (outputs JSON)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Transcribe all audio files in directory"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    # Handle directory mode
    if args.all or input_path.is_dir():
        results = transcribe_directory(
            str(input_path),
            args.backend,
            args.language,
        )
        output_text = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        # Single file mode
        result = transcribe_audio(
            str(input_path),
            args.backend,
            args.language,
            args.timestamps,
        )
        output_text = format_output(result, args.timestamps)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"\nSaved to: {output_path}")
    else:
        print("\n" + "=" * 60)
        print("TRANSCRIPTION")
        print("=" * 60)
        print(output_text)


if __name__ == "__main__":
    main()
