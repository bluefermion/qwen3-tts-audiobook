#!/usr/bin/env python3
"""
validate_audio.py - Validate TTS audio quality by detecting stuttering and artifacts

Transcribes audio using Whisper and analyzes for quality issues:
- Stuttering (repeated words/syllables)
- Word repetition
- Unusual gaps/pauses
- Incomplete sentences
- Gibberish or nonsense

Usage:
    # Validate a single audio file
    python scripts/validate_audio.py output/chunk_001.wav

    # Validate against expected text
    python scripts/validate_audio.py output/chunk_001.wav --expected "This is what it should say"

    # Validate all chunks in a directory
    python scripts/validate_audio.py output/chunks/ --all

    # Output detailed report
    python scripts/validate_audio.py output/podcast.mp3 --report -o report.json

    # Just check pass/fail (for automation)
    python scripts/validate_audio.py output/chunk.wav --strict

Exit codes:
    0 - All validations passed
    1 - Validation issues detected
    2 - Error (file not found, etc.)

Requires:
    pip install openai-whisper
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple

# Resolve paths and add to sys.path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


@dataclass
class ValidationIssue:
    """A single validation issue."""
    type: str           # stuttering, repetition, gap, incomplete, gibberish, mismatch
    severity: str       # warning, error
    message: str
    position: Optional[int] = None  # Character position in text
    context: Optional[str] = None   # Surrounding text


@dataclass
class ValidationResult:
    """Complete validation result for an audio file."""
    file: str
    passed: bool
    transcription: str
    expected: Optional[str]
    issues: List[ValidationIssue]
    similarity_score: Optional[float] = None
    duration: Optional[float] = None


def detect_stuttering(text: str) -> List[ValidationIssue]:
    """
    Detect stuttering patterns in transcribed text.

    Looks for:
    - Repeated words: "the the the"
    - Repeated syllables: "I-I-I", "wh-wh-what"
    - Repeated short phrases: "I want to I want to"
    """
    issues = []

    # Pattern 1: Repeated words (2+ times)
    # Matches: "the the", "I I I", "and and"
    word_repeat_pattern = r'\b(\w+)(?:\s+\1){1,}\b'
    for match in re.finditer(word_repeat_pattern, text, re.IGNORECASE):
        word = match.group(1)
        full_match = match.group(0)
        repeat_count = len(re.findall(r'\b' + re.escape(word) + r'\b', full_match, re.IGNORECASE))

        if repeat_count >= 2:
            issues.append(ValidationIssue(
                type="stuttering",
                severity="error" if repeat_count >= 3 else "warning",
                message=f"Repeated word '{word}' {repeat_count} times",
                position=match.start(),
                context=text[max(0, match.start()-20):match.end()+20],
            ))

    # Pattern 2: Hyphenated stutters (syllable repetition)
    # Matches: "I-I-I", "wh-wh-what", "b-b-but"
    syllable_stutter_pattern = r'\b([a-zA-Z]{1,3})(?:-\1){1,}(?:-?[a-zA-Z]*)\b'
    for match in re.finditer(syllable_stutter_pattern, text):
        issues.append(ValidationIssue(
            type="stuttering",
            severity="error",
            message=f"Syllable stutter detected: '{match.group(0)}'",
            position=match.start(),
            context=text[max(0, match.start()-20):match.end()+20],
        ))

    # Pattern 3: Repeated short phrases (2-4 words)
    # Matches: "I want to I want to", "this is a this is a"
    words = text.split()
    for phrase_len in [2, 3, 4]:
        for i in range(len(words) - phrase_len * 2 + 1):
            phrase1 = ' '.join(words[i:i+phrase_len])
            phrase2 = ' '.join(words[i+phrase_len:i+phrase_len*2])
            if phrase1.lower() == phrase2.lower() and len(phrase1) > 3:
                issues.append(ValidationIssue(
                    type="repetition",
                    severity="error",
                    message=f"Repeated phrase: '{phrase1}'",
                    position=text.lower().find(phrase1.lower()),
                    context=f"...{phrase1} {phrase2}...",
                ))

    return issues


def detect_gaps_and_incomplete(text: str) -> List[ValidationIssue]:
    """
    Detect unusual gaps and incomplete sentences.
    """
    issues = []

    # Multiple spaces (might indicate transcription gaps)
    if '   ' in text:
        issues.append(ValidationIssue(
            type="gap",
            severity="warning",
            message="Unusual gaps detected in transcription",
            context=text[:100],
        ))

    # Sentence fragments (very short segments between periods)
    sentences = re.split(r'[.!?]+', text)
    for i, sent in enumerate(sentences):
        sent = sent.strip()
        if sent and len(sent.split()) == 1 and len(sent) < 10:
            issues.append(ValidationIssue(
                type="incomplete",
                severity="warning",
                message=f"Possible incomplete sentence: '{sent}'",
                context=sent,
            ))

    # Trailing incomplete sentence (no ending punctuation)
    text_stripped = text.strip()
    if text_stripped and text_stripped[-1] not in '.!?':
        last_sentence = text_stripped.split('.')[-1].strip()
        if len(last_sentence.split()) > 2:
            issues.append(ValidationIssue(
                type="incomplete",
                severity="warning",
                message="Text may end mid-sentence",
                context=last_sentence[-50:],
            ))

    return issues


def detect_gibberish(text: str) -> List[ValidationIssue]:
    """
    Detect potential gibberish or nonsense in transcription.
    """
    issues = []

    # Very long words (likely transcription errors)
    for match in re.finditer(r'\b[a-zA-Z]{20,}\b', text):
        issues.append(ValidationIssue(
            type="gibberish",
            severity="error",
            message=f"Unusually long word: '{match.group(0)[:30]}...'",
            position=match.start(),
        ))

    # Repeated single characters (not normal words)
    for match in re.finditer(r'\b([a-zA-Z])\1{4,}\b', text):
        issues.append(ValidationIssue(
            type="gibberish",
            severity="error",
            message=f"Character repetition: '{match.group(0)}'",
            position=match.start(),
        ))

    # All consonants (no vowels) in long words
    consonant_only = re.finditer(r'\b[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{6,}\b', text)
    for match in consonant_only:
        issues.append(ValidationIssue(
            type="gibberish",
            severity="warning",
            message=f"Possible gibberish (no vowels): '{match.group(0)}'",
            position=match.start(),
        ))

    return issues


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between expected and actual text.
    Returns a score between 0.0 and 1.0.
    """
    # Normalize texts
    def normalize(t):
        t = t.lower()
        t = re.sub(r'[^\w\s]', '', t)
        t = ' '.join(t.split())
        return t

    t1 = normalize(text1)
    t2 = normalize(text2)

    if not t1 or not t2:
        return 0.0

    # Word-level comparison
    words1 = set(t1.split())
    words2 = set(t2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def compare_with_expected(transcription: str, expected: str) -> List[ValidationIssue]:
    """
    Compare transcription against expected text.
    """
    issues = []
    similarity = calculate_similarity(transcription, expected)

    if similarity < 0.5:
        issues.append(ValidationIssue(
            type="mismatch",
            severity="error",
            message=f"Low similarity to expected text: {similarity:.1%}",
            context=f"Expected: {expected[:100]}...\nGot: {transcription[:100]}...",
        ))
    elif similarity < 0.8:
        issues.append(ValidationIssue(
            type="mismatch",
            severity="warning",
            message=f"Moderate similarity to expected text: {similarity:.1%}",
        ))

    return issues


def validate_audio(
    audio_file: str,
    expected_text: Optional[str] = None,
    model_name: str = "base",
    language: Optional[str] = None,
) -> ValidationResult:
    """
    Validate audio quality by transcribing and analyzing.

    Args:
        audio_file: Path to audio file
        expected_text: Optional expected transcription
        model_name: Whisper model size
        language: Language code or None for auto-detect

    Returns:
        ValidationResult with all issues found
    """
    from transcribe import transcribe_audio

    # Transcribe
    result = transcribe_audio(audio_file, model_name, language, timestamps=False)
    transcription = result["text"]
    duration = result.get("duration", 0)

    # Collect all issues
    issues = []
    issues.extend(detect_stuttering(transcription))
    issues.extend(detect_gaps_and_incomplete(transcription))
    issues.extend(detect_gibberish(transcription))

    similarity_score = None
    if expected_text:
        issues.extend(compare_with_expected(transcription, expected_text))
        similarity_score = calculate_similarity(transcription, expected_text)

    # Determine pass/fail
    has_errors = any(issue.severity == "error" for issue in issues)
    passed = not has_errors

    return ValidationResult(
        file=audio_file,
        passed=passed,
        transcription=transcription,
        expected=expected_text,
        issues=issues,
        similarity_score=similarity_score,
        duration=duration,
    )


def validate_directory(
    directory: str,
    model_name: str = "base",
    language: Optional[str] = None,
    extensions: tuple = (".wav", ".mp3"),
) -> List[ValidationResult]:
    """Validate all audio files in a directory."""
    dir_path = Path(directory)
    audio_files = []
    for ext in extensions:
        audio_files.extend(dir_path.glob(f"*{ext}"))

    audio_files = sorted(audio_files)
    results = []

    print(f"Validating {len(audio_files)} files...")

    for audio_file in audio_files:
        try:
            result = validate_audio(str(audio_file), None, model_name, language)
            status = "PASS" if result.passed else "FAIL"
            issue_count = len(result.issues)
            print(f"  [{status}] {audio_file.name} - {issue_count} issues")
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {audio_file.name}: {e}")

    return results


def print_report(result: ValidationResult, verbose: bool = True):
    """Print a human-readable validation report."""
    print()
    print("=" * 60)
    print(f"VALIDATION REPORT: {Path(result.file).name}")
    print("=" * 60)

    status = "PASSED" if result.passed else "FAILED"
    print(f"Status: {status}")

    if result.duration:
        print(f"Duration: {result.duration:.1f}s")

    if result.similarity_score is not None:
        print(f"Similarity: {result.similarity_score:.1%}")

    print(f"Issues: {len(result.issues)}")

    if result.issues:
        print()
        print("Issues Found:")
        print("-" * 40)
        for issue in result.issues:
            icon = "!" if issue.severity == "error" else "?"
            print(f"  [{icon}] {issue.type.upper()}: {issue.message}")
            if verbose and issue.context:
                print(f"      Context: {issue.context[:60]}...")

    if verbose:
        print()
        print("Transcription:")
        print("-" * 40)
        print(result.transcription[:500])
        if len(result.transcription) > 500:
            print("...")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Validate TTS audio quality by detecting stuttering and artifacts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_audio.py output/chunk.wav
  python scripts/validate_audio.py output/chunk.wav --expected "Hello world"
  python scripts/validate_audio.py output/ --all
  python scripts/validate_audio.py output/podcast.mp3 --report -o report.json
  python scripts/validate_audio.py output/chunk.wav --strict
        """
    )

    parser.add_argument("input", help="Audio file or directory")
    parser.add_argument("-o", "--output", help="Output report file (JSON)")
    parser.add_argument(
        "--expected", "-e",
        help="Expected transcription text"
    )
    parser.add_argument(
        "--expected-file", "-f",
        help="File containing expected transcription"
    )
    parser.add_argument(
        "--model", "-m",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--language", "-l",
        help="Language code (e.g., 'en', 'fr')"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Validate all audio files in directory"
    )
    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Output detailed report"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 on any issues (for CI/automation)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (just pass/fail)"
    )

    args = parser.parse_args()

    # Get expected text
    expected_text = args.expected
    if args.expected_file:
        expected_text = Path(args.expected_file).read_text(encoding="utf-8").strip()

    input_path = Path(args.input)

    # Validate
    if args.all or input_path.is_dir():
        results = validate_directory(
            str(input_path),
            args.model,
            args.language,
        )
        all_passed = all(r.passed for r in results)

        if not args.quiet:
            print()
            passed_count = sum(1 for r in results if r.passed)
            print(f"Summary: {passed_count}/{len(results)} passed")

        if args.output:
            output_data = [asdict(r) for r in results]
            Path(args.output).write_text(
                json.dumps(output_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"Report saved to: {args.output}")

        sys.exit(0 if all_passed else 1)

    else:
        # Single file
        result = validate_audio(
            str(input_path),
            expected_text,
            args.model,
            args.language,
        )

        if args.quiet:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status}: {input_path.name}")
        elif args.report or args.output:
            if args.output:
                Path(args.output).write_text(
                    json.dumps(asdict(result), indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                print(f"Report saved to: {args.output}")
            else:
                print_report(result, verbose=True)
        else:
            print_report(result, verbose=False)

        if args.strict and not result.passed:
            sys.exit(1)
        elif not result.passed:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
