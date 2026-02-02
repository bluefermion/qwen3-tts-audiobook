#!/usr/bin/env python3
"""
map_emotions_to_voices.py - Map emotional instruction tags to voice profile names

Converts LLM-generated emotional tags like [warm and engaging] to actual
voice profile names like [narrator_warm].

Usage:
    python scripts/map_emotions_to_voices.py chapter_speech.txt -o chapter_podcast.txt
"""

import argparse
import re
import sys
from pathlib import Path

# Emotion keywords to voice profile mapping
EMOTION_MAP = {
    # Warm/friendly emotions -> narrator_warm
    "warm": "narrator_warm",
    "friendly": "narrator_warm",
    "welcoming": "narrator_warm",
    "engaging": "narrator_warm",
    "inviting": "narrator_warm",
    "kind": "narrator_warm",
    "gentle": "narrator_warm",

    # Calm/neutral emotions -> narrator_calm
    "calm": "narrator_calm",
    "measured": "narrator_calm",
    "neutral": "narrator_calm",
    "explanatory": "narrator_calm",
    "steady": "narrator_calm",
    "even": "narrator_calm",
    "relaxed": "narrator_calm",
    "soothing": "narrator_calm",

    # Serious/authoritative emotions -> narrator_serious
    "serious": "narrator_serious",
    "thoughtful": "narrator_serious",
    "grave": "narrator_serious",
    "authoritative": "narrator_serious",
    "important": "narrator_serious",
    "solemn": "narrator_serious",
    "weighty": "narrator_serious",
    "concerned": "narrator_serious",

    # Excited/energetic emotions -> narrator_excited
    "excited": "narrator_excited",
    "enthusiastic": "narrator_excited",
    "revelatory": "narrator_excited",
    "energetic": "narrator_excited",
    "passionate": "narrator_excited",
    "animated": "narrator_excited",
    "lively": "narrator_excited",
    "upbeat": "narrator_excited",
    "thrilled": "narrator_excited",

    # Reflective/philosophical -> narrator_calm (or create narrator_reflective)
    "reflective": "narrator_calm",
    "philosophical": "narrator_calm",
    "contemplative": "narrator_calm",
    "introspective": "narrator_calm",
    "pensive": "narrator_calm",
}

DEFAULT_VOICE = "narrator_calm"


def map_instruction_to_voice(instruction: str) -> str:
    """Map an instruction tag to a voice profile name."""
    instruction_lower = instruction.lower()

    # Check each emotion keyword
    for emotion, voice in EMOTION_MAP.items():
        if emotion in instruction_lower:
            return voice

    return DEFAULT_VOICE


def process_file(input_path: str, output_path: str, verbose: bool = False):
    """Process a speech file and map instructions to voice profiles."""
    content = Path(input_path).read_text(encoding="utf-8")

    # Pattern: [instruction text] at start of line or after newline
    pattern = r'\[([^\]]+)\]'

    mappings_made = []

    def replace_instruction(match):
        instruction = match.group(1)

        # Skip pause commands
        if instruction.lower().startswith("pause"):
            return match.group(0)

        voice = map_instruction_to_voice(instruction)
        mappings_made.append((instruction, voice))
        return f"[{voice}]"

    result = re.sub(pattern, replace_instruction, content)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result, encoding="utf-8")

    print(f"Processed: {input_path}")
    print(f"Output: {output_path}")
    print(f"Mappings: {len(mappings_made)}")

    if verbose and mappings_made:
        print("\nEmotion -> Voice mappings:")
        seen = set()
        for instruction, voice in mappings_made:
            key = (instruction[:30], voice)
            if key not in seen:
                print(f"  [{instruction[:40]}...] -> [{voice}]")
                seen.add(key)


def main():
    parser = argparse.ArgumentParser(
        description="Map emotional tags to voice profile names"
    )
    parser.add_argument("input", help="Input speech file with emotional tags")
    parser.add_argument("-o", "--output", help="Output file (default: input_podcast.txt)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show mappings")

    args = parser.parse_args()

    if args.output:
        output = args.output
    else:
        input_path = Path(args.input)
        output = str(input_path.parent / f"{input_path.stem.replace('_speech', '')}_podcast.txt")

    process_file(args.input, output, args.verbose)


if __name__ == "__main__":
    main()
