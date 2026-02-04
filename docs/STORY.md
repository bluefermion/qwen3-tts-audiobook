# The Voice Clone Chronicles

*A totally true story about teaching robots to talk like humans*

---

## Chapter 1: "Why Does My AI Sound Like a Bored DMV Employee?"

So there we were, trying to make audiobooks. We had this fancy AI that could read text aloud. Cool, right?

**Wrong.**

It sounded like a robot reading a phone book. No pauses between chapters. No emotion. Just endless monotone droning. Like that one teacher who made history sound like a grocery list.

> "the battle of waterloo was fought in 1815 napoleon lost moving on to chapter 47..."

Ugh.

## Chapter 2: "Let's Just Clone My Voice, How Hard Can It Be?"

Famous last words.

We found this model called Qwen3-TTS that promised voice cloning. The internet said "just give it 6 seconds of audio and boom - instant clone!"

We gave it 6 seconds.

It gave us... something. Like a drunk parrot trying to impersonate you through a broken phone. Sure, it *kinda* sounded like a human, but which human? Nobody knew.

## Chapter 3: "The 30-Second Rule"

Turns out, AI needs more than 6 seconds to learn your voice. Who knew?

We recorded 30 seconds of actual talking:

> "When we think about the future of civilization..."

(Yes, we read something pretentious. Don't judge.)

**Result:** MUCH better. The AI actually sounded like us now. Well, slightly-sedated-us, but progress!

## Chapter 4: "The Great Temperature Debate"

The documentation said: "Use temperature 1.2-1.5 for more expressive output!"

We cranked it to 1.5.

**The AI:** *starts speaking in tongues*

Turns out the max is 1.0. Going above that is like asking your GPS to "be creative" with directions. Don't.

**New rule:** Temperature 0.9 for slight variation. Never higher. Ever.

## Chapter 5: "The 25Hz Mirage"

We read a research paper (yes, we're nerds) that said there's a "25Hz model" that's better for long audio.

Cool! Let's use it!

**HuggingFace:** "401 Unauthorized. Model not found."

**Us:** But... the paper said...

**HuggingFace:** The paper can say whatever it wants. I have what I have.

**Lesson learned:** Academic papers describe what's *possible*. HuggingFace has what's *available*. These are not always the same thing.

## Chapter 6: "Silence is Golden (Literally)"

Here's something nobody tells you: pauses are 50% of good audio.

Without pauses:
> "Chapter1TheBeginningOfAllThingsInthebeginning..."

With pauses:
> "Chapter 1: The Beginning of All Things. [dramatic pause] In the beginning..."

We added:
- 1.5 seconds after chapter titles
- 1 second after section headers
- 0.4 seconds between paragraphs

Suddenly it sounded like a real audiobook instead of an auctioneer on espresso.

## Chapter 7: "The Cloudflare Boss Battle"

We tried connecting to an LLM API to clean up our text.

**Cloudflare:** "Blocked. You look suspicious."

**Us:** But we're legitimate!

**Cloudflare:** Your User-Agent says "Python-urllib". That's what bots use.

**Us:** We ARE using Python...

**Cloudflare:** Exactly. Blocked.

**The fix:** Tell Python to pretend it's curl. `User-Agent: curl/8.0`

Sometimes you have to lie to computers to get work done.

## Chapter 8: "Two Models, Two Purposes"

We discovered Qwen3-TTS actually has TWO models:

| Model | What it does | The catch |
|-------|-------------|-----------|
| **Base** | Clones your actual voice | No emotion control |
| **CustomVoice** | Built-in voices with emotion | Not YOUR voice |

So we can either:
- Sound like ourselves (but monotone)
- Sound expressive (but like a stranger)

**Our solution:** Record ourselves in different moods:
- `narrator_calm.wav` - for chill explanations
- `narrator_excited.wav` - for "this is amazing!" moments
- `narrator_urgent.wav` - for when the AI loses your money

Then use each as a separate voice profile. Hack? Yes. Works? Also yes.

## Chapter 9: "4000 Characters of Wisdom"

The model can technically handle 32,768 tokens (~100,000 characters).

But should it? No.

We tested chunk sizes:

| Chars | Result |
|-------|--------|
| 500 | Stable but choppy |
| 1500 | Pretty good |
| 4000 | Sweet spot for RTX 3090 |
| 10000 | GPU starts sweating |
| 100000 | Theoretical |

**Final answer:** 4000 characters per chunk. Big enough for smooth audio, small enough to not crash.

## Chapter 10: "The Pipeline That Works"

After all this chaos, we built a pipeline that actually works:

```
1. Write in Markdown (because we're fancy)
2. Run it through an LLM to clean up (fix "AI" → "A.I.", etc.)
3. Add [pause 1s] markers for breathing room
4. Feed to Qwen3-TTS with our cloned voice
5. Stitch audio chunks together
6. Export as MP3
7. Pretend we knew what we were doing all along
```

## The Moral of the Story

Building a voice cloning pipeline is like assembling IKEA furniture:
- The instructions are technically correct but practically useless
- You'll have leftover pieces you don't understand
- It takes 10x longer than advertised
- But when it finally works, you feel like a genius

**Total time spent:** Way too much
**Moments of despair:** Several
**Working audiobooks:** Yes!
**Was it worth it:** Absolutely

---

## Quick Reference (The Actually Useful Part)

### Settings That Work

```python
MAX_CHUNK_CHARS = 4000      # For RTX 3090 24GB
TEMPERATURE = 1.0           # Max value, use 0.9 for variety
PAUSE_AFTER_TITLE = 1500    # ms
PAUSE_BETWEEN_PARAGRAPHS = 400  # ms
```

### Voice Recording Tips

1. Record 20-30 seconds (not 6!)
2. Speak naturally, not robotically
3. Include varied intonation
4. Quiet room, no echo
5. Save as mono 24kHz WAV

### The Three Models

| Model | Use Case |
|-------|----------|
| `Qwen3-TTS-12Hz-1.7B-Base` | Clone YOUR voice |
| `Qwen3-TTS-12Hz-1.7B-CustomVoice` | Built-in voices + emotion |
| `Qwen3-TTS-12Hz-1.7B-VoiceDesign` | Design new voices from descriptions |

### The Magic Incantation

```bash
# Clone your voice
python scripts/voice_factory.py clone voices/my_voice.wav "Hello world" -o hello.wav

# Test a voice profile
python scripts/voice_factory.py test voices/my_voice.wav "Testing one two three"
```

---

*Written by someone who learned all of this the hard way.*
*Dedicated to everyone who's ever yelled at a computer.*

---

**P.S.** If your AI starts speaking in tongues, you probably set the temperature too high. We've all been there.
