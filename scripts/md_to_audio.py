#!/usr/bin/env python3
"""
md_to_audio.py - Convert markdown files to audio using voice cloning

A unified script for converting markdown documents to audio files.
Supports both single-voice narration and multi-speaker dialogue.

Usage:
    # Basic usage with default voice
    python scripts/md_to_audio.py document.md -o output.mp3

    # With specific voice profile
    python scripts/md_to_audio.py document.md --voice patrick_calm -o output.mp3

    # With LLM preprocessing (requires DEMETERICS_API_KEY in .env)
    python scripts/md_to_audio.py document.md --preprocess -o output.mp3

    # French document
    python scripts/md_to_audio.py document_fr.md --language French -o output_fr.mp3
"""

import argparse
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple, Optional

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VOICES_DIR = PROJECT_ROOT / "voices"
OUTPUT_DIR = PROJECT_ROOT / "output"
VENV_PYTHON = PROJECT_ROOT / "venv_qwen3" / "bin" / "python"

# Default configuration
DEFAULT_VOICE = "patrick_30s_mono24k"
MAX_CHUNK_CHARS = 4000
LANGUAGE = "English"

# Pause durations (milliseconds)
PAUSE_AFTER_TITLE = 1500
PAUSE_AFTER_SECTION = 1000
PAUSE_AFTER_SUBSECTION = 700
PAUSE_BETWEEN_PARAGRAPHS = 400
PAUSE_BETWEEN_CHUNKS = 300


def strip_markdown(text: str) -> str:
    """Remove inline markdown formatting."""
    if not text:
        return ""

    t = text
    # Bold/italic
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", t)
    t = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", t)
    # Code
    t = re.sub(r"`([^`]+)`", r"\1", t)
    # Links
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # Images
    t = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", t)
    # HTML
    t = re.sub(r"<[^>]+>", "", t)
    # Curly braces
    t = re.sub(r"\{[^}]+\}", "", t)
    # Normalize
    t = t.replace("\u201c", '"').replace("\u201d", '"')
    t = t.replace("\u2018", "'").replace("\u2019", "'")
    t = t.replace("\u2014", " - ").replace("\u2013", " - ")
    t = t.replace("\u2026", "...")

    return t.strip()


def fix_pronunciation(text: str) -> str:
    """Fix acronyms and special terms for TTS."""
    replacements = {
        r"\bAI\b": "A.I.",
        r"\bAPI\b": "A.P.I.",
        r"\bCEO\b": "C.E.O.",
        r"\bGDP\b": "G.D.P.",
        r"\b90/10\b": "ninety-ten",
        r"\b80/20\b": "eighty-twenty",
        r"\bvs\.\b": "versus",
        r"\bvs\b": "versus",
        r"\be\.g\.\b": "for example",
        r"\bi\.e\.\b": "that is",
        r"\betc\.\b": "etcetera",
        r"\bLLM\b": "L.L.M.",
        r"\bLLMs\b": "L.L.M.s",
        r"\bGPT\b": "G.P.T.",
        r"\bURL\b": "U.R.L.",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def parse_markdown(content: str, max_chars: int = MAX_CHUNK_CHARS) -> List[Tuple[str, str, int]]:
    """
    Parse markdown into segments.

    Returns: List of (type, text, pause_after_ms)
    """
    segments = []
    lines = content.split("\n")
    current_paragraph = []
    in_code_block = False

    # Remove YAML frontmatter
    content_start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                content_start = i + 1
                break
    lines = lines[content_start:]

    def flush_paragraph():
        nonlocal current_paragraph
        if current_paragraph:
            text = " ".join(current_paragraph)
            text = strip_markdown(text)
            text = fix_pronunciation(text)
            text = " ".join(text.split())
            if text and len(text) > 2:
                # Split into chunks if needed
                chunks = split_into_chunks(text, max_chars)
                for i, chunk in enumerate(chunks):
                    pause = PAUSE_BETWEEN_PARAGRAPHS if i == len(chunks) - 1 else PAUSE_BETWEEN_CHUNKS
                    segments.append(("text", chunk, pause))
            current_paragraph = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if not stripped:
            flush_paragraph()
            continue

        if re.match(r"^[-*_]{3,}$", stripped):
            flush_paragraph()
            continue

        if stripped.startswith("|"):
            continue

        header_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header_match:
            flush_paragraph()
            level = len(header_match.group(1))
            header_text = strip_markdown(header_match.group(2))
            header_text = fix_pronunciation(header_text)

            if level == 1:
                segments.append(("title", header_text, PAUSE_AFTER_TITLE))
            elif level <= 3:
                segments.append(("section", header_text, PAUSE_AFTER_SECTION))
            else:
                segments.append(("subsection", header_text, PAUSE_AFTER_SUBSECTION))
            continue

        current_paragraph.append(stripped)

    flush_paragraph()
    return segments


def split_into_chunks(text: str, max_chars: int) -> List[str]:
    """Split text at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current = []
    current_len = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        if current_len + len(sent) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0

        current.append(sent)
        current_len += len(sent) + 1

    if current:
        chunks.append(" ".join(current))

    return [c.strip() for c in chunks if c.strip()]


def generate_audio(
    text: str,
    voice_path: Path,
    output_path: Path,
    language: str = "English",
) -> bool:
    """Generate audio for text using voice cloning."""
    import subprocess

    # Check for transcription (ICL mode)
    trans_path = voice_path.with_suffix(".txt")
    use_icl = trans_path.exists()

    script = f'''
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
)

ref_audio = "{voice_path}"
text = """{text}"""
'''

    if use_icl:
        trans_text = trans_path.read_text(encoding="utf-8").strip()
        script += f'''
ref_text = """{trans_text}"""
wavs, sr = model.generate_voice_clone(
    text=text,
    language="{language}",
    ref_audio=ref_audio,
    ref_text=ref_text,
)
'''
    else:
        script += f'''
wavs, sr = model.generate_voice_clone(
    text=text,
    language="{language}",
    ref_audio=ref_audio,
    x_vector_only_mode=True,
)
'''

    script += f'''
sf.write("{output_path}", wavs[0], sr)
'''

    result = subprocess.run(
        [str(VENV_PYTHON), "-c", script],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def combine_audio(
    audio_files: List[Path],
    pause_durations: List[int],
    output_path: Path,
) -> float:
    """Combine audio files with pauses."""
    from pydub import AudioSegment

    combined = AudioSegment.empty()

    for i, audio_file in enumerate(audio_files):
        if audio_file.exists():
            audio = AudioSegment.from_wav(str(audio_file))
            combined += audio

            if i < len(pause_durations) and pause_durations[i] > 0:
                combined += AudioSegment.silent(duration=pause_durations[i])

    if str(output_path).lower().endswith('.mp3'):
        combined.export(str(output_path), format="mp3", bitrate="192k")
    else:
        combined.export(str(output_path), format="wav")

    return len(combined) / 1000


def main():
    parser = argparse.ArgumentParser(
        description="Convert markdown to audio with voice cloning"
    )
    parser.add_argument("input", help="Input markdown file")
    parser.add_argument("-o", "--output", help="Output audio file")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"Voice profile name (default: {DEFAULT_VOICE})")
    parser.add_argument("--language", default=LANGUAGE, help=f"Language (default: {LANGUAGE})")
    parser.add_argument("--max-chars", type=int, default=MAX_CHUNK_CHARS, help="Max chars per chunk")
    parser.add_argument("--keep-chunks", action="store_true", help="Keep temp files")

    args = parser.parse_args()

    # Check input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    # Check voice
    voice_path = VOICES_DIR / f"{args.voice}.wav"
    if not voice_path.exists():
        print(f"Error: Voice not found: {voice_path}")
        print("\nAvailable voices:")
        for v in VOICES_DIR.glob("*.wav"):
            print(f"  {v.stem}")
        print("\nCreate a voice with: python scripts/voice_factory.py prepare recording.mp3 --name my_voice")
        sys.exit(1)

    # Set output
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = OUTPUT_DIR / f"{input_path.stem}.mp3"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse markdown
    print(f"Reading: {input_path}")
    content = input_path.read_text(encoding="utf-8")
    segments = parse_markdown(content, args.max_chars)
    print(f"Parsed {len(segments)} segments")

    # Generate audio
    temp_dir = Path(tempfile.mkdtemp(prefix="md_audio_"))
    audio_files = []
    pause_durations = []
    failed = 0

    print(f"\nGenerating audio with voice: {args.voice}")
    start_time = time.time()

    for i, (seg_type, text, pause_ms) in enumerate(segments):
        chunk_file = temp_dir / f"chunk_{i:04d}.wav"
        audio_files.append(chunk_file)
        pause_durations.append(pause_ms)

        print(f"  [{i+1}/{len(segments)}] {seg_type}: {text[:40]}...")

        success = generate_audio(text, voice_path, chunk_file, args.language)
        if not success:
            from pydub import AudioSegment
            AudioSegment.silent(duration=500).export(str(chunk_file), format="wav")
            failed += 1

    elapsed = time.time() - start_time

    # Combine
    print(f"\nCombining {len(audio_files)} segments...")
    duration = combine_audio(audio_files, pause_durations, output_path)

    # Cleanup
    if not args.keep_chunks:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    file_size = output_path.stat().st_size / (1024 * 1024)

    print()
    print("=" * 60)
    print("AUDIO COMPLETE")
    print("=" * 60)
    print(f"Output:   {output_path}")
    print(f"Duration: {duration/60:.1f} minutes")
    print(f"Size:     {file_size:.1f} MB")
    print(f"Segments: {len(segments)} ({failed} failed)")
    print(f"Time:     {elapsed/60:.1f} minutes")
    print("=" * 60)


if __name__ == "__main__":
    main()
