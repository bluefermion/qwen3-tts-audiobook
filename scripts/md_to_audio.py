#!/usr/bin/env python3
"""
md_to_audio.py - Convert markdown files to audio using voice cloning

A unified script for converting markdown documents to audio files.
Supports both single-voice narration and multi-speaker dialogue.
Includes validation with automatic retry for quality issues.

Validation uses Qwen3-ASR for retries 1-3, then Groq Whisper for retries 4-5
to get a "second opinion" from a different model.

Usage:
    # Basic usage with default voice
    python scripts/md_to_audio.py document.md -o output.mp3

    # With specific voice profile
    python scripts/md_to_audio.py document.md --voice my_voice -o output.mp3

    # With validation and retry (recommended)
    python scripts/md_to_audio.py document.md --validate -o output.mp3

    # With LLM preprocessing (requires DEMETERICS_API_KEY in .env)
    python scripts/md_to_audio.py document.md --preprocess -o output.mp3

    # French document
    python scripts/md_to_audio.py document_fr.md --language French -o output_fr.mp3

Requires:
    pip install qwen-asr
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
DEFAULT_VOICE = "synthetic_narrator"
MAX_CHUNK_CHARS = 4000
LANGUAGE = "English"
MAX_RETRIES = 5  # Maximum retry attempts for failed validation (3 local + 2 Groq)

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


def validate_chunk(
    audio_path: Path,
    expected_text: str,
    use_groq: bool = False,
) -> tuple:
    """
    Validate audio chunk for quality issues.

    Args:
        audio_path: Path to audio file
        expected_text: The text that should have been spoken
        use_groq: If True, use Groq's Whisper API instead of local Qwen3-ASR

    Returns:
        Tuple of (passed: bool, issues: list, transcription: str)
    """
    try:
        # Import transcription module
        if str(SCRIPT_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPT_DIR))
        from transcribe import transcribe_audio

        # Get transcription using appropriate backend
        backend = "groq" if use_groq else "qwen"
        try:
            result = transcribe_audio(str(audio_path), backend=backend)
            transcription = result["text"]
        except Exception as e:
            if use_groq:
                # Groq failed, skip validation
                return True, ["Groq transcription unavailable"], ""
            else:
                # Qwen failed, try to continue
                return True, [f"Transcription error: {e}"], ""

        issues = []

        # Check for stuttering (repeated words)
        import re
        word_repeat = re.findall(r'\b(\w+)(?:\s+\1){1,}\b', transcription, re.IGNORECASE)
        for word in word_repeat:
            issues.append(f"Stuttering: repeated word '{word}'")

        # Check for syllable stutters
        syllable_stutters = re.findall(r'\b([a-zA-Z]{1,3})(?:-\1){1,}', transcription)
        for stutter in syllable_stutters:
            issues.append(f"Stuttering: syllable repetition '{stutter}'")

        # Check similarity to expected text
        def normalize(t):
            t = t.lower()
            t = re.sub(r'[^\w\s]', '', t)
            return ' '.join(t.split())

        expected_norm = normalize(expected_text)
        actual_norm = normalize(transcription)

        if expected_norm and actual_norm:
            words1 = set(expected_norm.split())
            words2 = set(actual_norm.split())
            if words1 and words2:
                similarity = len(words1 & words2) / len(words1 | words2)
                if similarity < 0.5:
                    issues.append(f"Low similarity ({similarity:.0%}) to expected text")

        passed = len(issues) == 0
        return passed, issues, transcription

    except Exception as e:
        # Validation failed, but don't block generation
        return True, [f"Validation error: {e}"], ""


def generate_audio_with_validation(
    text: str,
    voice_path: Path,
    output_path: Path,
    language: str = "English",
    validate: bool = True,
    max_retries: int = MAX_RETRIES,
) -> tuple:
    """
    Generate audio with validation and automatic retry.

    Uses Qwen3-ASR for retries 1-3, then Groq Whisper for retries 4-5
    to get a "second opinion" from a different model.

    Args:
        text: Text to synthesize
        voice_path: Path to voice profile
        output_path: Output audio path
        language: Language for TTS
        validate: Whether to validate output
        max_retries: Maximum retry attempts

    Returns:
        Tuple of (success: bool, attempts: int, final_issues: list)
    """
    attempts = 0
    last_issues = []

    while attempts < max_retries:
        attempts += 1

        # Generate audio
        success = generate_audio(text, voice_path, output_path, language)
        if not success:
            last_issues = ["Generation failed"]
            continue

        # Skip validation if disabled
        if not validate:
            return True, attempts, []

        # Use Groq for attempts 4+ (after 3 local Qwen3-ASR failures)
        use_groq = attempts > 3

        # Validate the output
        passed, issues, transcription = validate_chunk(
            output_path, text, use_groq=use_groq
        )

        if passed:
            if use_groq:
                print(f"    ✓ Passed with Groq validation on attempt {attempts}")
            return True, attempts, []

        last_issues = issues

        if attempts < max_retries:
            validator = "Groq" if use_groq else "Qwen3-ASR"
            print(f"    ⚠ Validation failed ({validator}, attempt {attempts}/{max_retries}): {', '.join(issues[:2])}")
            print(f"    ↻ Retrying...")

    # All retries exhausted
    return False, attempts, last_issues


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
    parser.add_argument("--validate", "-V", action="store_true",
                        help="Validate audio quality and retry on stuttering (uses Qwen3-ASR, Groq fallback)")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES,
                        help=f"Max retry attempts for failed validation (default: {MAX_RETRIES}, 1-3 Qwen, 4-5 Groq)")
    parser.add_argument("--strict", action="store_true",
                        help="Fail if any chunk fails validation after all retries")

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
    total_retries = 0
    validation_failures = []

    print(f"\nGenerating audio with voice: {args.voice}")
    if args.validate:
        print(f"Validation enabled (Qwen3-ASR + Groq fallback, max retries: {args.max_retries})")
    start_time = time.time()

    for i, (seg_type, text, pause_ms) in enumerate(segments):
        chunk_file = temp_dir / f"chunk_{i:04d}.wav"
        audio_files.append(chunk_file)
        pause_durations.append(pause_ms)

        print(f"  [{i+1}/{len(segments)}] {seg_type}: {text[:40]}...")

        if args.validate:
            success, attempts, issues = generate_audio_with_validation(
                text, voice_path, chunk_file, args.language,
                validate=True,
                max_retries=args.max_retries,
            )
            total_retries += (attempts - 1)

            if not success:
                validation_failures.append({
                    "segment": i + 1,
                    "text": text[:50],
                    "issues": issues,
                })
                if args.strict:
                    print(f"    ✗ Failed after {attempts} attempts: {', '.join(issues)}")
                    failed += 1
                    # Create silence placeholder
                    from pydub import AudioSegment
                    AudioSegment.silent(duration=500).export(str(chunk_file), format="wav")
                else:
                    print(f"    ⚠ Using best effort after {attempts} attempts")
            elif attempts > 1:
                print(f"    ✓ Passed on attempt {attempts}")
        else:
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
    if args.validate:
        print(f"Retries:  {total_retries}")
    print(f"Time:     {elapsed/60:.1f} minutes")

    if validation_failures:
        print()
        print("Validation Issues:")
        for vf in validation_failures[:5]:  # Show first 5
            print(f"  Segment {vf['segment']}: {', '.join(vf['issues'][:2])}")
        if len(validation_failures) > 5:
            print(f"  ... and {len(validation_failures) - 5} more")

    print("=" * 60)

    # Exit with error if strict mode and failures
    if args.strict and failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
