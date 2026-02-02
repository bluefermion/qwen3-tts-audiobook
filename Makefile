# ============================================================================
# Qwen3-TTS Voice Cloning Toolkit - Makefile
# ============================================================================
#
# Usage:
#   make              Show help
#   make ui           Launch terminal UI
#   make voices       List voice profiles
#   make prepare      Prepare a new voice profile
#   make test         Test a voice profile
#   make convert      Convert markdown to audio
#   make podcast      Generate multi-speaker podcast
#
# ============================================================================

.PHONY: help ui install check voices demo-voice prepare test convert podcast examples clean clean-all

# Configuration
SHELL := /bin/bash
PYTHON := python3
VENV := venv_qwen3
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
SCRIPTS := scripts
VOICES := voices
OUTPUT := output
EXAMPLES := examples

# Colors
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m
COLOR_CYAN := \033[36m
COLOR_DIM := \033[2m

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================

help: ## Show this help
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)  Qwen3-TTS Voice Cloning Toolkit$(COLOR_RESET)"
	@echo "$(COLOR_DIM)  ─────────────────────────────────$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)  Quick Start:$(COLOR_RESET)"
	@echo "    make install         Install dependencies"
	@echo "    make ui              Launch interactive terminal UI"
	@echo ""
	@echo "$(COLOR_BOLD)  Voice Management:$(COLOR_RESET)"
	@echo "    make voices          List all voice profiles"
	@echo "    make demo-voice      Download public domain demo voice"
	@echo "    make prepare         Prepare a new voice profile"
	@echo "    make test            Test a voice profile"
	@echo ""
	@echo "$(COLOR_BOLD)  Audio Generation:$(COLOR_RESET)"
	@echo "    make convert         Convert markdown to audio"
	@echo "    make podcast         Generate multi-speaker podcast"
	@echo "    make examples        Show example commands"
	@echo ""
	@echo "$(COLOR_BOLD)  Maintenance:$(COLOR_RESET)"
	@echo "    make check           Check environment setup"
	@echo "    make clean           Clean generated output"
	@echo "    make clean-all       Clean everything (including venv)"
	@echo ""
	@echo "$(COLOR_DIM)  Run 'make <target>' for more details on each command.$(COLOR_RESET)"
	@echo ""

# ============================================================================
# Setup & Environment
# ============================================================================

install: ## Install dependencies and setup environment
	@echo "$(COLOR_BLUE)Setting up Qwen3-TTS environment...$(COLOR_RESET)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@echo "Installing dependencies..."
	@$(VENV_PIP) install --upgrade pip
	@$(VENV_PIP) install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
	@$(VENV_PIP) install qwen-tts soundfile pydub tqdm textual rich
	@mkdir -p $(VOICES) $(OUTPUT)
	@echo "$(COLOR_GREEN)✓ Installation complete$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_YELLOW)Optional: Install FlashAttention for 2x speed:$(COLOR_RESET)"
	@echo "  $(VENV_PIP) install flash-attn --no-build-isolation"
	@echo ""

check: ## Check environment setup
	@echo "$(COLOR_BLUE)Checking environment...$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_BOLD)Python:$(COLOR_RESET)"
	@if [ -f "$(VENV_PYTHON)" ]; then \
		echo "  $(COLOR_GREEN)✓$(COLOR_RESET) venv: $(VENV_PYTHON)"; \
		$(VENV_PYTHON) --version; \
	else \
		echo "  $(COLOR_YELLOW)✗$(COLOR_RESET) venv not found - run 'make install'"; \
	fi
	@echo ""
	@echo "$(COLOR_BOLD)GPU:$(COLOR_RESET)"
	@if command -v nvidia-smi &> /dev/null; then \
		nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader; \
	else \
		echo "  $(COLOR_YELLOW)✗$(COLOR_RESET) nvidia-smi not available"; \
	fi
	@echo ""
	@echo "$(COLOR_BOLD)Dependencies:$(COLOR_RESET)"
	@if [ -f "$(VENV_PYTHON)" ]; then \
		$(VENV_PYTHON) -c "import torch; print(f'  torch: {torch.__version__}')" 2>/dev/null || echo "  $(COLOR_YELLOW)✗$(COLOR_RESET) torch not installed"; \
		$(VENV_PYTHON) -c "import qwen_tts; print('  qwen_tts: OK')" 2>/dev/null || echo "  $(COLOR_YELLOW)✗$(COLOR_RESET) qwen_tts not installed"; \
		$(VENV_PYTHON) -c "import textual; print(f'  textual: {textual.__version__}')" 2>/dev/null || echo "  $(COLOR_YELLOW)✗$(COLOR_RESET) textual not installed (UI won't work)"; \
	fi
	@echo ""
	@echo "$(COLOR_BOLD)Voices:$(COLOR_RESET)"
	@count=$$(ls -1 $(VOICES)/*.wav 2>/dev/null | wc -l); \
	echo "  $$count voice profile(s) in $(VOICES)/"
	@echo ""

# ============================================================================
# Terminal UI
# ============================================================================

ui: check-venv ## Launch interactive terminal UI
	@echo "$(COLOR_BLUE)Launching TTS UI...$(COLOR_RESET)"
	@$(VENV_PYTHON) tts_ui.py

# ============================================================================
# Voice Management
# ============================================================================

voices: ## List all voice profiles
	@echo "$(COLOR_BOLD)Voice Profiles$(COLOR_RESET)"
	@echo "──────────────"
	@if [ -f "$(VENV_PYTHON)" ]; then \
		$(VENV_PYTHON) $(SCRIPTS)/voice_factory.py list; \
	else \
		echo "Scanning $(VOICES)/..."; \
		for f in $(VOICES)/*.wav; do \
			[ -e "$$f" ] || continue; \
			name=$$(basename "$$f" .wav); \
			if [ -f "$(VOICES)/$$name.txt" ]; then \
				echo "  $$name [ICL]"; \
			else \
				echo "  $$name [x_vector]"; \
			fi; \
		done; \
	fi

demo-voice: ## Download public domain demo voice (LibriVox)
	@echo "$(COLOR_BOLD)Demo Voice Setup$(COLOR_RESET)"
	@echo "────────────────"
	@./$(EXAMPLES)/demo_voices/setup_demo_voice.sh

prepare: check-venv ## Prepare a new voice profile
	@echo "$(COLOR_BOLD)Prepare Voice Profile$(COLOR_RESET)"
	@echo "─────────────────────"
	@echo ""
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make prepare FILE=recording.mp3 NAME=my_voice [TRANS=\"transcription\"]"; \
		echo ""; \
		echo "Arguments:"; \
		echo "  FILE   Path to audio recording (required)"; \
		echo "  NAME   Name for the voice profile (required)"; \
		echo "  TRANS  Transcription for ICL mode (optional)"; \
		echo ""; \
		echo "Example:"; \
		echo "  make prepare FILE=~/recording.mp3 NAME=patrick_calm"; \
		echo "  make prepare FILE=~/recording.mp3 NAME=patrick_calm TRANS=\"Hello, this is a test...\""; \
		exit 1; \
	fi
	@if [ -z "$(NAME)" ]; then \
		echo "$(COLOR_YELLOW)Error: NAME is required$(COLOR_RESET)"; \
		echo "Usage: make prepare FILE=recording.mp3 NAME=my_voice"; \
		exit 1; \
	fi
	@if [ -n "$(TRANS)" ]; then \
		$(VENV_PYTHON) $(SCRIPTS)/voice_factory.py prepare "$(FILE)" --name "$(NAME)" --transcription "$(TRANS)"; \
	else \
		$(VENV_PYTHON) $(SCRIPTS)/voice_factory.py prepare "$(FILE)" --name "$(NAME)"; \
	fi

test: check-venv ## Test a voice profile
	@echo "$(COLOR_BOLD)Test Voice Profile$(COLOR_RESET)"
	@echo "──────────────────"
	@echo ""
	@if [ -z "$(VOICE)" ]; then \
		echo "Usage: make test VOICE=my_voice [TEXT=\"Hello world\"]"; \
		echo ""; \
		echo "Arguments:"; \
		echo "  VOICE  Name of the voice profile (required)"; \
		echo "  TEXT   Text to synthesize (default: test phrase)"; \
		echo ""; \
		echo "Available voices:"; \
		@for f in $(VOICES)/*.wav; do \
			[ -e "$$f" ] || continue; \
			echo "  $$(basename "$$f" .wav)"; \
		done; \
		exit 1; \
	fi
	@text="$(TEXT)"; \
	if [ -z "$$text" ]; then \
		text="Hello, this is a test of my cloned voice. How does it sound?"; \
	fi; \
	$(VENV_PYTHON) $(SCRIPTS)/voice_factory.py test $(VOICES)/$(VOICE).wav "$$text"

# ============================================================================
# Audio Generation
# ============================================================================

convert: check-venv ## Convert markdown to audio
	@echo "$(COLOR_BOLD)Convert to Audio$(COLOR_RESET)"
	@echo "────────────────"
	@echo ""
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make convert FILE=document.md [VOICE=my_voice] [LANG=English] [OUT=output.mp3]"; \
		echo ""; \
		echo "Arguments:"; \
		echo "  FILE   Input markdown file (required)"; \
		echo "  VOICE  Voice profile name (default: first available)"; \
		echo "  LANG   Language: English, French, Chinese, etc. (default: English)"; \
		echo "  OUT    Output file path (default: output/<filename>.mp3)"; \
		echo ""; \
		echo "Example:"; \
		echo "  make convert FILE=examples/english/sample.md VOICE=patrick_calm"; \
		exit 1; \
	fi
	@voice="$(VOICE)"; \
	if [ -z "$$voice" ]; then \
		voice=$$(ls -1 $(VOICES)/*.wav 2>/dev/null | head -1 | xargs -I{} basename {} .wav); \
		if [ -z "$$voice" ]; then \
			echo "$(COLOR_YELLOW)Error: No voice profiles found. Run 'make prepare' first.$(COLOR_RESET)"; \
			exit 1; \
		fi; \
		echo "Using voice: $$voice"; \
	fi; \
	lang="$(LANG)"; \
	if [ -z "$$lang" ]; then lang="English"; fi; \
	cmd="$(VENV_PYTHON) $(SCRIPTS)/md_to_audio.py \"$(FILE)\" --voice $$voice --language $$lang"; \
	if [ -n "$(OUT)" ]; then \
		cmd="$$cmd -o \"$(OUT)\""; \
	fi; \
	eval $$cmd

podcast: check-venv ## Generate multi-speaker podcast
	@echo "$(COLOR_BOLD)Multi-Speaker Podcast$(COLOR_RESET)"
	@echo "─────────────────────"
	@echo ""
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make podcast FILE=script.txt [OUT=podcast.mp3] [LANG=English]"; \
		echo ""; \
		echo "Arguments:"; \
		echo "  FILE   Script file with speaker tags (required)"; \
		echo "  OUT    Output file path (default: output/<filename>.mp3)"; \
		echo "  LANG   Language (default: English)"; \
		echo ""; \
		echo "Script format:"; \
		echo "  [speaker_name] Text to speak"; \
		echo "  [pause 1s]     Add a pause"; \
		echo "  # Comment      Ignored line"; \
		echo ""; \
		echo "Example:"; \
		echo "  make podcast FILE=examples/english/podcast_demo.txt"; \
		exit 1; \
	fi
	@lang="$(LANG)"; \
	if [ -z "$$lang" ]; then lang="English"; fi; \
	cmd="$(VENV_PYTHON) $(SCRIPTS)/multi_speaker.py \"$(FILE)\" --language $$lang"; \
	if [ -n "$(OUT)" ]; then \
		cmd="$$cmd -o \"$(OUT)\""; \
	fi; \
	eval $$cmd

# ============================================================================
# Examples
# ============================================================================

examples: ## Show example commands
	@echo "$(COLOR_BOLD)Example Commands$(COLOR_RESET)"
	@echo "────────────────"
	@echo ""
	@echo "$(COLOR_CYAN)1. Prepare a voice from recording:$(COLOR_RESET)"
	@echo "   make prepare FILE=~/my_recording.mp3 NAME=my_voice"
	@echo ""
	@echo "$(COLOR_CYAN)2. Test the voice:$(COLOR_RESET)"
	@echo "   make test VOICE=my_voice TEXT=\"Hello, world!\""
	@echo ""
	@echo "$(COLOR_CYAN)3. Convert sample markdown to audio:$(COLOR_RESET)"
	@echo "   make convert FILE=examples/english/sample.md VOICE=my_voice"
	@echo ""
	@echo "$(COLOR_CYAN)4. Generate French audio:$(COLOR_RESET)"
	@echo "   make convert FILE=examples/french/exemple.md VOICE=my_voice LANG=French"
	@echo ""
	@echo "$(COLOR_CYAN)5. Create multi-speaker podcast:$(COLOR_RESET)"
	@echo "   make podcast FILE=examples/english/podcast_demo.txt"
	@echo ""
	@echo "$(COLOR_CYAN)6. Launch interactive UI:$(COLOR_RESET)"
	@echo "   make ui"
	@echo ""

# ============================================================================
# Maintenance
# ============================================================================

clean: ## Clean generated output
	@echo "$(COLOR_BLUE)Cleaning output files...$(COLOR_RESET)"
	@rm -f $(OUTPUT)/*.mp3 $(OUTPUT)/*.wav
	@echo "$(COLOR_GREEN)✓ Cleaned$(COLOR_RESET)"

clean-all: clean ## Clean everything including venv
	@echo "$(COLOR_BLUE)Cleaning all...$(COLOR_RESET)"
	@rm -rf $(VENV)
	@rm -rf __pycache__ $(SCRIPTS)/__pycache__
	@echo "$(COLOR_GREEN)✓ Cleaned all$(COLOR_RESET)"

# ============================================================================
# Internal Helpers
# ============================================================================

check-venv:
	@if [ ! -f "$(VENV_PYTHON)" ]; then \
		echo "$(COLOR_YELLOW)Error: Virtual environment not found$(COLOR_RESET)"; \
		echo "Run: make install"; \
		exit 1; \
	fi
