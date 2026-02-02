# Contributing to qwen3-tts-audiobook

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a virtual environment and install dependencies:
   ```bash
   make install
   ```

## Development Workflow

1. Create a branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes

3. Test your changes:
   ```bash
   make check
   make demo-voice
   make test VOICE=synthetic_narrator
   ```

4. Commit with a clear message:
   ```bash
   git commit -m "feat: add your feature description"
   ```

5. Push and create a Pull Request

## Code Style

- Use Python type hints where practical
- Follow existing patterns in the codebase
- Keep scripts modular and focused
- Add docstrings to new functions

## Areas for Contribution

- **New languages**: Add examples in other languages
- **Documentation**: Improve guides or add tutorials
- **Voice profiles**: Better default voice descriptions
- **Performance**: GPU memory optimization
- **Testing**: Add automated tests

## Questions?

Open an issue for discussion before starting large changes.
