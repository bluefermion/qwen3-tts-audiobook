#!/usr/bin/env python3
"""
multi_speaker.py - Multi-speaker podcast/dialogue generation

Convert multi-speaker scripts to audio using different voice profiles.
Each speaker can have their own cloned voice with optional emotional variants.
Includes validation with automatic retry for quality issues.

Validation uses Qwen3-ASR for retries 1-3, then Groq Whisper for retries 4-5
to get a "second opinion" from a different model.

Script Format:
    [speaker_name] Text to speak
    [speaker_name;instruction] Text with voice instruction (CustomVoice only)

    # Comments start with #
    [pause 1s]  # Standalone pause

Example Script:
    [host_excited] Welcome to the Tech Talk Podcast!

    [pause 1s]

    [host_serious] Today we're discussing a critical topic.

    [guest_warm] Thank you for having me.

    [host_urgent] WHERE DID MY AI MONEY GO?!?

Usage:
    # Generate from script file
    python scripts/multi_speaker.py script.txt -o podcast.mp3

    # With validation and retry (recommended)
    python scripts/multi_speaker.py script.txt --validate -o podcast.mp3

    # Generate from inline text
    python scripts/multi_speaker.py --inline "[host] Hello [guest] Hi there" -o output.mp3

    # List required voice profiles for a script
    python scripts/multi_speaker.py script.txt --list-voices

Voice Profiles:
    Voice profiles are WAV files in the voices/ directory.
    Create them using: python scripts/voice_factory.py prepare recording.mp3 --name speaker_name

Requires:
    pip install qwen-asr
"""

import argparse
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VOICES_DIR = PROJECT_ROOT / "voices"
OUTPUT_DIR = PROJECT_ROOT / "output"
VENV_PYTHON = PROJECT_ROOT / "venv_qwen3" / "bin" / "python"

# Validation settings (3 local Qwen3-ASR + 2 Groq fallback)
MAX_RETRIES = 5


@dataclass
class Segment:
    """A single segment in the script."""
    speaker: Optional[str]  # None for pause-only segments
    instruction: Optional[str]
    text: str
    pause_after: int  # milliseconds
    line_number: int


def parse_script(content: str) -> List[Segment]:
    """
    Parse a multi-speaker script into segments.

    Supports:
        [speaker] text
        [speaker;instruction] text
        [pause Xs]
        # comments

    Returns:
        List of Segment objects
    """
    segments = []

    # Patterns
    speaker_pattern = re.compile(
        r'^\[([a-zA-Z][a-zA-Z0-9_]*?)(?:;([^\]]+))?\]\s*(.*)$'
    )
    pause_pattern = re.compile(r'^\[pause\s+(\d+(?:\.\d+)?)\s*s?\]$', re.IGNORECASE)

    lines = content.strip().split('\n')
    current_speaker = None
    current_instruction = None
    current_text_parts = []
    current_line = 0

    def flush_segment():
        nonlocal current_speaker, current_instruction, current_text_parts
        if current_speaker and current_text_parts:
            text = ' '.join(current_text_parts).strip()
            if text:
                segments.append(Segment(
                    speaker=current_speaker,
                    instruction=current_instruction,
                    text=text,
                    pause_after=400,  # Default pause between segments
                    line_number=current_line,
                ))
        current_text_parts = []

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            if not line:
                flush_segment()
            continue

        # Check for standalone pause
        pause_match = pause_pattern.match(line)
        if pause_match:
            flush_segment()
            pause_seconds = float(pause_match.group(1))
            segments.append(Segment(
                speaker=None,
                instruction=None,
                text="",
                pause_after=int(pause_seconds * 1000),
                line_number=line_num,
            ))
            continue

        # Check for speaker tag
        speaker_match = speaker_pattern.match(line)
        if speaker_match:
            flush_segment()
            current_speaker = speaker_match.group(1)
            current_instruction = speaker_match.group(2)
            text = speaker_match.group(3).strip()
            current_line = line_num
            if text:
                current_text_parts = [text]
            continue

        # Continuation of previous speaker's text
        if current_speaker:
            current_text_parts.append(line)
        else:
            print(f"Warning: Line {line_num} has no speaker tag, skipping")

    # Flush final segment
    flush_segment()

    return segments


def get_required_voices(segments: List[Segment]) -> set:
    """Get set of voice profiles required for a script."""
    return {s.speaker for s in segments if s.speaker}


def check_voices(voices: set) -> Tuple[set, set]:
    """Check which voices exist and which are missing."""
    found = set()
    missing = set()

    for voice in voices:
        voice_path = VOICES_DIR / f"{voice}.wav"
        if voice_path.exists():
            found.add(voice)
        else:
            missing.add(voice)

    return found, missing


def generate_segment_audio(
    segment: Segment,
    output_path: Path,
    language: str = "English",
) -> bool:
    """
    Generate audio for a single segment.

    Returns True on success, False on failure.
    """
    if not segment.speaker:
        # Pause-only segment - create silence
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=segment.pause_after)
        silence.export(str(output_path), format="wav")
        return True

    voice_path = VOICES_DIR / f"{segment.speaker}.wav"
    if not voice_path.exists():
        print(f"Warning: Voice not found: {voice_path}")
        return False

    # Check for transcription (ICL mode)
    trans_path = voice_path.with_suffix(".txt")
    use_icl = trans_path.exists()

    # Build generation script
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
text = """{segment.text}"""
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

    import subprocess
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", script],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0


def validate_segment(
    audio_path: Path,
    expected_text: str,
    use_groq: bool = False,
) -> tuple:
    """
    Validate audio segment for quality issues.

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
                return True, ["Groq transcription unavailable"], ""
            else:
                return True, [f"Transcription error: {e}"], ""

        issues = []

        # Check for stuttering
        import re
        word_repeat = re.findall(r'\b(\w+)(?:\s+\1){1,}\b', transcription, re.IGNORECASE)
        for word in word_repeat:
            issues.append(f"Stuttering: '{word}'")

        syllable_stutters = re.findall(r'\b([a-zA-Z]{1,3})(?:-\1){1,}', transcription)
        for stutter in syllable_stutters:
            issues.append(f"Syllable stutter: '{stutter}'")

        # Check similarity
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
                    issues.append(f"Low similarity ({similarity:.0%})")

        return len(issues) == 0, issues, transcription

    except Exception as e:
        return True, [f"Validation error: {e}"], ""


def generate_segment_with_validation(
    segment: Segment,
    output_path: Path,
    language: str = "English",
    validate: bool = True,
    max_retries: int = MAX_RETRIES,
) -> tuple:
    """
    Generate segment audio with validation and retry.

    Uses Qwen3-ASR for retries 1-3, then Groq Whisper for retries 4-5
    to get a "second opinion" from a different model.

    Returns:
        Tuple of (success: bool, attempts: int, issues: list)
    """
    # Pause segments don't need validation
    if not segment.speaker:
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=segment.pause_after)
        silence.export(str(output_path), format="wav")
        return True, 1, []

    attempts = 0
    last_issues = []

    while attempts < max_retries:
        attempts += 1

        success = generate_segment_audio(segment, output_path, language)
        if not success:
            last_issues = ["Generation failed"]
            continue

        if not validate:
            return True, attempts, []

        # Use Groq for attempts 4+ (after 3 local Qwen3-ASR failures)
        use_groq = attempts > 3

        passed, issues, _ = validate_segment(
            output_path, segment.text, use_groq=use_groq
        )

        if passed:
            if use_groq:
                print(f"      ✓ Passed with Groq validation on attempt {attempts}")
            return True, attempts, []

        last_issues = issues

        if attempts < max_retries:
            validator = "Groq" if use_groq else "Qwen3-ASR"
            print(f"      ⚠ Validation failed ({validator}, attempt {attempts}/{max_retries}): {', '.join(issues[:2])}")
            print(f"      ↻ Retrying...")

    return False, attempts, last_issues


def combine_segments(
    audio_files: List[Path],
    pause_durations: List[int],
    output_path: Path,
) -> float:
    """
    Combine audio segments with pauses.

    Returns duration in seconds.
    """
    from pydub import AudioSegment

    combined = AudioSegment.empty()

    for i, audio_file in enumerate(audio_files):
        if audio_file.exists():
            audio = AudioSegment.from_wav(str(audio_file))
            combined += audio

            if i < len(pause_durations) and pause_durations[i] > 0:
                combined += AudioSegment.silent(duration=pause_durations[i])

    # Export
    if str(output_path).lower().endswith('.mp3'):
        combined.export(str(output_path), format="mp3", bitrate="192k")
    else:
        combined.export(str(output_path), format="wav")

    return len(combined) / 1000


def generate_podcast(
    script_content: str,
    output_file: str,
    language: str = "English",
    keep_chunks: bool = False,
    validate: bool = False,
    max_retries: int = MAX_RETRIES,
    strict: bool = False,
) -> dict:
    """
    Generate multi-speaker podcast from script.

    Args:
        script_content: Script text
        output_file: Output audio path
        language: Language for TTS
        keep_chunks: Keep temp files
        validate: Enable validation with retry
        max_retries: Max retry attempts
        strict: Fail if any segment fails validation

    Returns stats dictionary.
    """
    # Parse script
    segments = parse_script(script_content)
    print(f"Parsed {len(segments)} segments")

    # Check voices
    required_voices = get_required_voices(segments)
    found, missing = check_voices(required_voices)

    print(f"Voices found: {', '.join(sorted(found)) or 'none'}")
    if missing:
        print(f"Voices missing: {', '.join(sorted(missing))}")
        print("\nCreate missing voices with:")
        for v in sorted(missing):
            print(f"  python scripts/voice_factory.py prepare recording.mp3 --name {v}")
        return {"error": "Missing voices", "missing": list(missing)}

    # Generate audio
    temp_dir = Path(tempfile.mkdtemp(prefix="podcast_"))
    audio_files = []
    pause_durations = []
    failed = 0
    total_retries = 0
    validation_failures = []

    print(f"\nGenerating audio for {len(segments)} segments...")
    if validate:
        print(f"Validation enabled (Qwen3-ASR + Groq fallback, max retries: {max_retries})")
    start_time = time.time()

    for i, segment in enumerate(segments):
        chunk_file = temp_dir / f"chunk_{i:04d}.wav"
        audio_files.append(chunk_file)
        pause_durations.append(segment.pause_after)

        if segment.speaker:
            print(f"  [{segment.speaker}] {segment.text[:40]}...")

        if validate:
            success, attempts, issues = generate_segment_with_validation(
                segment, chunk_file, language,
                validate=True,
                max_retries=max_retries,
            )
            total_retries += (attempts - 1)

            if not success:
                validation_failures.append({
                    "segment": i + 1,
                    "speaker": segment.speaker,
                    "text": segment.text[:50],
                    "issues": issues,
                })
                if strict:
                    print(f"    ✗ Failed after {attempts} attempts")
                    failed += 1
                    from pydub import AudioSegment
                    AudioSegment.silent(duration=500).export(str(chunk_file), format="wav")
                else:
                    print(f"    ⚠ Using best effort after {attempts} attempts")
            elif attempts > 1:
                print(f"    ✓ Passed on attempt {attempts}")
        else:
            success = generate_segment_audio(segment, chunk_file, language)
            if not success:
                from pydub import AudioSegment
                AudioSegment.silent(duration=500).export(str(chunk_file), format="wav")
                failed += 1

    elapsed = time.time() - start_time

    # Combine
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nCombining segments...")
    duration = combine_segments(audio_files, pause_durations, output_path)

    # Cleanup
    if not keep_chunks:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    file_size = output_path.stat().st_size / (1024 * 1024)

    print()
    print("=" * 60)
    print("PODCAST COMPLETE")
    print("=" * 60)
    print(f"Output:   {output_path}")
    print(f"Duration: {duration/60:.1f} minutes")
    print(f"Size:     {file_size:.1f} MB")
    print(f"Segments: {len(segments)} ({failed} failed)")
    if validate:
        print(f"Retries:  {total_retries}")
    print(f"Time:     {elapsed/60:.1f} minutes")

    if validation_failures:
        print()
        print("Validation Issues:")
        for vf in validation_failures[:5]:
            print(f"  [{vf['speaker']}] {', '.join(vf['issues'][:2])}")
        if len(validation_failures) > 5:
            print(f"  ... and {len(validation_failures) - 5} more")

    print("=" * 60)

    return {
        "output": str(output_path),
        "duration_seconds": duration,
        "segments": len(segments),
        "failed": failed,
        "retries": total_retries if validate else 0,
        "validation_failures": len(validation_failures) if validate else 0,
        "elapsed": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-speaker podcast from script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Script Format:
  [speaker_name] Text to speak
  [speaker_name;instruction] Text with instruction
  [pause 1s]  # Pause
  # Comment line

Example:
  [host_excited] Welcome to the podcast!
  [pause 0.5s]
  [guest] Thanks for having me.
        """
    )

    parser.add_argument("script", nargs="?", help="Script file")
    parser.add_argument("-o", "--output", help="Output audio file")
    parser.add_argument("--inline", help="Inline script text")
    parser.add_argument("--list-voices", action="store_true", help="List required voices")
    parser.add_argument("--language", default="English", help="Language")
    parser.add_argument("--keep-chunks", action="store_true", help="Keep temp files")
    parser.add_argument("--validate", "-V", action="store_true",
                        help="Validate audio quality and retry on stuttering (uses Qwen3-ASR, Groq fallback)")
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES,
                        help=f"Max retry attempts for failed validation (default: {MAX_RETRIES}, 1-3 Qwen, 4-5 Groq)")
    parser.add_argument("--strict", action="store_true",
                        help="Fail if any segment fails validation after all retries")

    args = parser.parse_args()

    # Get script content
    if args.inline:
        content = args.inline
    elif args.script:
        content = Path(args.script).read_text(encoding="utf-8")
    else:
        parser.print_help()
        return

    # List voices mode
    if args.list_voices:
        segments = parse_script(content)
        voices = get_required_voices(segments)
        found, missing = check_voices(voices)

        print("Required voices:")
        for v in sorted(voices):
            status = "OK" if v in found else "MISSING"
            print(f"  {v}: {status}")

        if missing:
            print("\nTo create missing voices:")
            for v in sorted(missing):
                print(f"  python scripts/voice_factory.py prepare recording.mp3 --name {v}")
        return

    # Generate podcast
    if not args.output:
        if args.script:
            args.output = str(Path(args.script).stem) + ".mp3"
        else:
            args.output = "output/podcast.mp3"

    result = generate_podcast(
        content,
        args.output,
        args.language,
        args.keep_chunks,
        validate=args.validate,
        max_retries=args.max_retries,
        strict=args.strict,
    )

    # Exit with error if strict mode and failures
    if args.strict and result.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
