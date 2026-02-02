#!/usr/bin/env python3
"""
preprocess_for_tts.py - LLM preprocessing for better TTS output

Uses an LLM to clean and prepare text for natural-sounding speech:
- Expands abbreviations (AI -> A.I., etc. -> etcetera)
- Adds [pause Xs] markers for natural pacing
- Removes markdown formatting artifacts
- Optionally adds [instruction] tags for emotional guidance

Usage:
    # Basic preprocessing
    python scripts/preprocess_for_tts.py document.md -o document_speech.txt

    # With voice instructions (for emotional variants)
    python scripts/preprocess_for_tts.py document.md --with-instructions -o document_speech.txt

    # Then generate audio
    python scripts/md_to_audio.py document_speech.txt --voice patrick -o output.mp3

Requires:
    DEMETERICS_API_KEY in environment or .env file
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Load .env if present
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


def call_llm(prompt: str, system_prompt: str) -> str:
    """Call LLM API for text processing."""
    import json
    import urllib.request
    import urllib.error

    api_key = os.environ.get("DEMETERICS_API_KEY")
    if not api_key:
        print("Error: DEMETERICS_API_KEY not set", file=sys.stderr)
        print("Set it in .env or environment", file=sys.stderr)
        sys.exit(1)

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 8000,
    }

    req = urllib.request.Request(
        "https://api.demeterics.com/groq/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "curl/8.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"API Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)


SYSTEM_PROMPT_BASIC = """You are a text preprocessor for text-to-speech (TTS) systems.

Transform the input text to be spoken naturally:

1. PRONUNCIATION FIXES:
   - AI → A.I.
   - API → A.P.I.
   - CEO → C.E.O.
   - GDP → G.D.P.
   - LLM → L.L.M.
   - vs. → versus
   - e.g. → for example
   - i.e. → that is
   - etc. → etcetera

2. PAUSE MARKERS (insert these for natural pacing):
   - [pause 1.5s] after chapter/section titles
   - [pause 1s] after major paragraph breaks
   - [pause 0.5s] for dramatic effect or list items

3. CLEANUP:
   - Remove markdown formatting (**, __, `, etc.)
   - Remove URLs and image references
   - Remove table formatting
   - Convert bullet lists to flowing prose or add pauses between items

4. NUMBERS:
   - Write numbers as words when appropriate
   - 90/10 → ninety-ten
   - 80/20 → eighty-twenty

Output ONLY the processed text, ready to be spoken. No explanations."""

SYSTEM_PROMPT_WITH_INSTRUCTIONS = """You are a text preprocessor for expressive text-to-speech (TTS) systems.

Transform the input text with BOTH cleanup AND emotional guidance:

1. Apply all standard TTS preprocessing (abbreviations, pauses, cleanup)

2. ADD VOICE INSTRUCTION TAGS at the start of sections to guide tone:
   - [warm and engaging] for welcoming/friendly sections
   - [serious and measured] for important warnings or data
   - [excited and energetic] for breakthroughs or discoveries
   - [calm and reflective] for philosophical passages
   - [urgent] for calls to action

Example output:
[warm and engaging] Welcome to the future of voice technology.

[pause 1s]

[serious and measured] The statistics reveal a troubling trend. Over sixty percent of users reported concerns.

[pause 0.5s]

[excited and energetic] But here's the breakthrough - we've solved it!

Output ONLY the processed text with instruction tags. No explanations."""


def preprocess_markdown(input_file: str, output_file: str, with_instructions: bool = False) -> None:
    """Preprocess markdown file for TTS."""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    content = input_path.read_text(encoding="utf-8")

    # Remove YAML frontmatter
    if content.startswith("---"):
        end_idx = content.find("---", 3)
        if end_idx > 0:
            content = content[end_idx + 3:].strip()

    print(f"Processing: {input_file}")
    print(f"Input length: {len(content)} chars")
    print(f"Mode: {'with voice instructions' if with_instructions else 'basic'}")

    # Choose system prompt
    system_prompt = SYSTEM_PROMPT_WITH_INSTRUCTIONS if with_instructions else SYSTEM_PROMPT_BASIC

    # Process in chunks if too long
    MAX_CHUNK = 6000
    if len(content) > MAX_CHUNK:
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\n+', content)
        chunks = []
        current_chunk = []
        current_len = 0

        for para in paragraphs:
            if current_len + len(para) > MAX_CHUNK and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_len = 0
            current_chunk.append(para)
            current_len += len(para)

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        print(f"Split into {len(chunks)} chunks for processing")

        processed_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            processed = call_llm(chunk, system_prompt)
            processed_chunks.append(processed)

        result = '\n\n[pause 1s]\n\n'.join(processed_chunks)
    else:
        result = call_llm(content, system_prompt)

    # Write output
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result, encoding="utf-8")

    print(f"Output: {output_file}")
    print(f"Output length: {len(result)} chars")


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess text for TTS using LLM"
    )
    parser.add_argument("input", help="Input markdown or text file")
    parser.add_argument("-o", "--output", help="Output file (default: input_speech.txt)")
    parser.add_argument("--with-instructions", action="store_true",
                        help="Add voice instruction tags for emotional guidance")

    args = parser.parse_args()

    if args.output:
        output = args.output
    else:
        input_path = Path(args.input)
        output = str(input_path.parent / f"{input_path.stem}_speech.txt")

    preprocess_markdown(args.input, output, args.with_instructions)


if __name__ == "__main__":
    main()
