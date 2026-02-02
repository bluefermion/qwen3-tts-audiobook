#!/usr/bin/env python3
"""
transcribe.py - Transcribe audio files using OpenAI Whisper locally

Converts audio files (mp3, wav, etc.) to text using the Whisper model.
Useful for quality validation of TTS output.

Usage:
    # Transcribe a single file
    python scripts/transcribe.py output/audiobook.mp3

    # Transcribe with specific model size
    python scripts/transcribe.py output/audiobook.mp3 --model medium

    # Output to file instead of stdout
    python scripts/transcribe.py output/audiobook.mp3 -o transcription.txt

    # Transcribe all files in a directory
    python scripts/transcribe.py output/ --all

    # Get word-level timestamps (for validation)
    python scripts/transcribe.py output/chunk.wav --timestamps -o chunk.json

Models (accuracy vs speed):
    tiny   - Fastest, least accurate (~1GB VRAM)
    base   - Fast, decent accuracy (~1GB VRAM)
    small  - Good balance (~2GB VRAM)
    medium - High accuracy (~5GB VRAM)
    large  - Best accuracy (~10GB VRAM)

Requires:
    pip install openai-whisper
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


def transcribe_audio(
    audio_file: str,
    model_name: str = "base",
    language: Optional[str] = None,
    timestamps: bool = False,
) -> dict:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_file: Path to audio file
        model_name: Whisper model size (tiny, base, small, medium, large)
        language: Language code (e.g., "en", "fr") or None for auto-detect
        timestamps: Whether to include word-level timestamps

    Returns:
        Dictionary with transcription results
    """
    import whisper

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    print(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)

    print(f"Transcribing: {audio_path.name}")

    # Transcribe with options
    result = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=timestamps,
        verbose=False,
    )

    return {
        "file": str(audio_path),
        "text": result["text"].strip(),
        "language": result.get("language", language),
        "segments": result.get("segments", []),
        "duration": result.get("segments", [{}])[-1].get("end", 0) if result.get("segments") else 0,
    }


def format_output(result: dict, timestamps: bool = False) -> str:
    """Format transcription result for display."""
    if timestamps:
        return json.dumps(result, indent=2, ensure_ascii=False)
    else:
        return result["text"]


def transcribe_directory(
    directory: str,
    model_name: str = "base",
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
            result = transcribe_audio(str(audio_file), model_name, language)
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
        description="Transcribe audio files using Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/transcribe.py output/test.wav
  python scripts/transcribe.py output/podcast.mp3 --model medium
  python scripts/transcribe.py output/chunk.wav --timestamps -o chunk.json
  python scripts/transcribe.py output/ --all -o transcriptions.json
        """
    )

    parser.add_argument("input", help="Audio file or directory")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--language", "-l",
        help="Language code (e.g., 'en', 'fr'). Auto-detect if not specified."
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
            args.model,
            args.language,
        )
        output_text = json.dumps(results, indent=2, ensure_ascii=False)
    else:
        # Single file mode
        result = transcribe_audio(
            str(input_path),
            args.model,
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
