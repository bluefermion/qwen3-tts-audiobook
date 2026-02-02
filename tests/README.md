# Tests

This directory is for automated tests (future work).

## Manual Testing

For now, use the Makefile targets:

```bash
# Check environment
make check

# Create and test a synthetic voice
make demo-voice
make test VOICE=synthetic_narrator TEXT="Hello, this is a test."

# Test markdown conversion
make convert FILE=examples/english/sample.md VOICE=synthetic_narrator
```
