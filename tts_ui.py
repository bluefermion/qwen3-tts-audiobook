#!/usr/bin/env python3
"""
tts_ui.py - Terminal UI for Qwen3-TTS Voice Cloning Toolkit

A modern, keyboard-driven interface for managing voice profiles,
converting documents to audio, and monitoring TTS generation.

Usage:
    python tts_ui.py
    # or
    make ui

Keyboard Shortcuts:
    q / Ctrl+C  - Quit
    Tab         - Switch panels
    Enter       - Select / Execute
    p           - Prepare new voice
    t           - Test selected voice
    c           - Convert file to audio
    m           - Multi-speaker mode
    l           - View logs
    r           - Refresh file list
    ?           - Help
"""

import asyncio
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Button, DataTable, DirectoryTree, Footer, Header, Input,
        Label, ListItem, ListView, Log, ProgressBar, Rule, Select,
        Static, TabbedContent, TabPane, Tree
    )
    from textual.screen import ModalScreen
    from textual import work
    from textual.worker import Worker, get_current_worker
except ImportError:
    print("Error: textual not installed")
    print("Install with: pip install textual")
    sys.exit(1)

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR
VOICES_DIR = PROJECT_ROOT / "voices"
OUTPUT_DIR = PROJECT_ROOT / "output"
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
VENV_PYTHON = PROJECT_ROOT / "venv_qwen3" / "bin" / "python"


# ============================================================================
# Styles
# ============================================================================
CSS = """
Screen {
    background: $surface;
}

#main-container {
    height: 100%;
    width: 100%;
}

#left-panel {
    width: 35%;
    height: 100%;
    border: solid $primary;
    padding: 0 1;
}

#right-panel {
    width: 65%;
    height: 100%;
    border: solid $secondary;
    padding: 0 1;
}

#voices-list {
    height: 1fr;
}

#status-bar {
    dock: bottom;
    height: 3;
    background: $primary-darken-2;
    padding: 0 1;
}

#status-text {
    width: 100%;
}

.panel-title {
    text-style: bold;
    color: $text;
    background: $primary;
    padding: 0 1;
    width: 100%;
    text-align: center;
}

.voice-item {
    padding: 0 1;
}

.voice-item:hover {
    background: $primary-darken-1;
}

.voice-selected {
    background: $primary;
}

Log {
    height: 1fr;
    border: solid $secondary-darken-1;
}

#action-buttons {
    height: auto;
    padding: 1;
    layout: horizontal;
}

#action-buttons Button {
    margin: 0 1;
}

.modal-dialog {
    width: 60;
    height: auto;
    border: thick $primary;
    background: $surface;
    padding: 1 2;
}

.modal-dialog Input {
    margin: 1 0;
}

.modal-dialog Button {
    margin: 1 1 0 0;
}

#progress-container {
    height: 3;
    padding: 0 1;
}

ProgressBar {
    width: 100%;
}

DataTable {
    height: 1fr;
}

.info-label {
    color: $text-muted;
}

.success {
    color: $success;
}

.error {
    color: $error;
}

.warning {
    color: $warning;
}
"""


# ============================================================================
# Modal Dialogs
# ============================================================================
class PrepareVoiceModal(ModalScreen):
    """Modal for preparing a new voice profile."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog"):
            yield Label("Prepare New Voice Profile", classes="panel-title")
            yield Label("Audio file path:")
            yield Input(placeholder="/path/to/recording.mp3", id="audio-path")
            yield Label("Voice name:")
            yield Input(placeholder="my_voice", id="voice-name")
            yield Label("Transcription (optional, for ICL mode):")
            yield Input(placeholder="What you said in the recording...", id="transcription")
            with Horizontal():
                yield Button("Prepare", variant="primary", id="btn-prepare")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-prepare":
            audio_path = self.query_one("#audio-path", Input).value
            voice_name = self.query_one("#voice-name", Input).value
            transcription = self.query_one("#transcription", Input).value
            if audio_path and voice_name:
                self.dismiss((audio_path, voice_name, transcription))
            else:
                self.app.notify("Please fill in audio path and voice name", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TestVoiceModal(ModalScreen):
    """Modal for testing a voice profile."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, voice_name: str):
        super().__init__()
        self.voice_name = voice_name

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog"):
            yield Label(f"Test Voice: {self.voice_name}", classes="panel-title")
            yield Label("Text to synthesize:")
            yield Input(
                placeholder="Hello, this is a test of my cloned voice!",
                id="test-text",
                value="Hello, this is a test of my cloned voice!"
            )
            with Horizontal():
                yield Button("Generate", variant="primary", id="btn-generate")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            text = self.query_one("#test-text", Input).value
            if text:
                self.dismiss(text)
            else:
                self.app.notify("Please enter text to synthesize", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConvertFileModal(ModalScreen):
    """Modal for converting a file to audio."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, voices: list[str]):
        super().__init__()
        self.voices = voices

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog"):
            yield Label("Convert File to Audio", classes="panel-title")
            yield Label("Input file (markdown or text):")
            yield Input(placeholder="/path/to/document.md", id="input-file")
            yield Label("Voice profile:")
            yield Select(
                [(v, v) for v in self.voices] if self.voices else [("(no voices)", "")],
                id="voice-select",
                prompt="Select voice"
            )
            yield Label("Output file (optional):")
            yield Input(placeholder="output/my_audio.mp3", id="output-file")
            yield Label("Language:")
            yield Select(
                [("English", "English"), ("French", "French"), ("Chinese", "Chinese"),
                 ("Japanese", "Japanese"), ("Korean", "Korean")],
                id="language-select",
                value="English"
            )
            with Horizontal():
                yield Button("Convert", variant="primary", id="btn-convert")
                yield Button("Cancel", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-convert":
            input_file = self.query_one("#input-file", Input).value
            voice = self.query_one("#voice-select", Select).value
            output_file = self.query_one("#output-file", Input).value
            language = self.query_one("#language-select", Select).value
            if input_file and voice:
                self.dismiss((input_file, voice, output_file, language))
            else:
                self.app.notify("Please fill in input file and select a voice", severity="error")
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class HelpModal(ModalScreen):
    """Help screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Container(classes="modal-dialog"):
            yield Label("Keyboard Shortcuts", classes="panel-title")
            yield Static("""
[bold]Navigation[/bold]
  Tab        Switch panels
  ↑/↓        Navigate lists
  Enter      Select item

[bold]Actions[/bold]
  p          Prepare new voice
  t          Test selected voice
  c          Convert file to audio
  m          Multi-speaker podcast
  r          Refresh file lists

[bold]General[/bold]
  ?          Show this help
  q          Quit application
  Ctrl+C     Quit application

[bold]In Modals[/bold]
  Escape     Cancel/Close
  Tab        Next field
  Enter      Submit
            """)
            yield Button("Close", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


# ============================================================================
# Main Application
# ============================================================================
class TTSApp(App):
    """Main TTS UI Application."""

    TITLE = "Qwen3-TTS Voice Cloning Toolkit"
    CSS = CSS

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "prepare_voice", "Prepare Voice"),
        Binding("t", "test_voice", "Test Voice"),
        Binding("c", "convert_file", "Convert"),
        Binding("m", "multi_speaker", "Multi-Speaker"),
        Binding("r", "refresh", "Refresh"),
        Binding("question_mark", "show_help", "Help"),
        Binding("tab", "focus_next", "Next Panel", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.selected_voice: Optional[str] = None
        self.voices: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            # Left panel - Voice profiles
            with Vertical(id="left-panel"):
                yield Static("Voice Profiles", classes="panel-title")
                yield DataTable(id="voices-table")

                yield Static("Quick Actions", classes="panel-title")
                with Vertical(id="action-buttons"):
                    yield Button("Prepare Voice [p]", id="btn-prepare", variant="primary")
                    yield Button("Test Voice [t]", id="btn-test")
                    yield Button("Convert File [c]", id="btn-convert", variant="success")
                    yield Button("Multi-Speaker [m]", id="btn-multi")

            # Right panel - Logs and output
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("Logs", id="tab-logs"):
                        yield Log(id="log-viewer", highlight=True, markup=True)

                    with TabPane("Output Files", id="tab-output"):
                        yield DataTable(id="output-table")

                    with TabPane("Examples", id="tab-examples"):
                        yield DataTable(id="examples-table")

        # Status bar
        with Horizontal(id="status-bar"):
            yield Static("Ready", id="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the UI when mounted."""
        self.log_message("Qwen3-TTS Voice Cloning Toolkit started")
        self.log_message(f"Project root: {PROJECT_ROOT}")

        # Setup tables
        self.setup_voices_table()
        self.setup_output_table()
        self.setup_examples_table()

        # Load initial data
        self.refresh_voices()
        self.refresh_output()
        self.refresh_examples()

        # Check environment
        self.check_environment()

    def setup_voices_table(self) -> None:
        """Setup the voices table columns."""
        table = self.query_one("#voices-table", DataTable)
        table.add_columns("Name", "Duration", "Mode", "Status")
        table.cursor_type = "row"

    def setup_output_table(self) -> None:
        """Setup the output files table."""
        table = self.query_one("#output-table", DataTable)
        table.add_columns("File", "Size", "Modified")
        table.cursor_type = "row"

    def setup_examples_table(self) -> None:
        """Setup the examples table."""
        table = self.query_one("#examples-table", DataTable)
        table.add_columns("File", "Type", "Language")
        table.cursor_type = "row"

    def log_message(self, message: str, level: str = "info") -> None:
        """Add a message to the log viewer."""
        log = self.query_one("#log-viewer", Log)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if level == "error":
            log.write_line(f"[red]{timestamp}[/red] [bold red]ERROR[/bold red] {message}")
        elif level == "warning":
            log.write_line(f"[yellow]{timestamp}[/yellow] [bold yellow]WARN[/bold yellow] {message}")
        elif level == "success":
            log.write_line(f"[green]{timestamp}[/green] [bold green]OK[/bold green] {message}")
        else:
            log.write_line(f"[dim]{timestamp}[/dim] {message}")

    def set_status(self, message: str) -> None:
        """Update the status bar."""
        status = self.query_one("#status-text", Static)
        status.update(message)

    def check_environment(self) -> None:
        """Check if the environment is properly configured."""
        # Check venv
        if VENV_PYTHON.exists():
            self.log_message(f"Python venv: {VENV_PYTHON}", "success")
        else:
            self.log_message(f"Python venv not found: {VENV_PYTHON}", "warning")
            self.log_message("Run: python3 -m venv venv_qwen3 && pip install qwen-tts", "info")

        # Check voices directory
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Check GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                gpu_info = result.stdout.strip()
                self.log_message(f"GPU: {gpu_info}", "success")
            else:
                self.log_message("GPU: nvidia-smi failed", "warning")
        except Exception:
            self.log_message("GPU: nvidia-smi not available", "warning")

    def refresh_voices(self) -> None:
        """Refresh the list of voice profiles."""
        table = self.query_one("#voices-table", DataTable)
        table.clear()
        self.voices = []

        if not VOICES_DIR.exists():
            return

        for wav_file in sorted(VOICES_DIR.glob("*.wav")):
            name = wav_file.stem
            self.voices.append(name)

            # Get duration
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", str(wav_file)],
                    capture_output=True, text=True, timeout=5
                )
                import json
                info = json.loads(result.stdout)
                duration = float(info.get("format", {}).get("duration", 0))
                duration_str = f"{duration:.1f}s"
            except Exception:
                duration_str = "?"

            # Check for transcription (ICL mode)
            trans_path = wav_file.with_suffix(".txt")
            mode = "ICL" if trans_path.exists() else "x_vector"

            table.add_row(name, duration_str, mode, "Ready")

        if self.voices:
            self.log_message(f"Loaded {len(self.voices)} voice profile(s)")
        else:
            self.log_message("No voice profiles found in voices/", "warning")

    def refresh_output(self) -> None:
        """Refresh the list of output files."""
        table = self.query_one("#output-table", DataTable)
        table.clear()

        if not OUTPUT_DIR.exists():
            return

        for audio_file in sorted(OUTPUT_DIR.glob("*.mp3")) + sorted(OUTPUT_DIR.glob("*.wav")):
            name = audio_file.name
            size = audio_file.stat().st_size / (1024 * 1024)
            size_str = f"{size:.1f} MB"
            mtime = datetime.fromtimestamp(audio_file.stat().st_mtime)
            mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            table.add_row(name, size_str, mtime_str)

    def refresh_examples(self) -> None:
        """Refresh the examples list."""
        table = self.query_one("#examples-table", DataTable)
        table.clear()

        if not EXAMPLES_DIR.exists():
            return

        for example_file in sorted(EXAMPLES_DIR.rglob("*.*")):
            if example_file.is_file():
                name = str(example_file.relative_to(EXAMPLES_DIR))

                if example_file.suffix == ".md":
                    file_type = "Markdown"
                elif example_file.suffix == ".txt":
                    file_type = "Script"
                else:
                    file_type = example_file.suffix

                # Detect language from path
                if "french" in str(example_file).lower():
                    language = "French"
                elif "english" in str(example_file).lower():
                    language = "English"
                else:
                    language = "?"

                table.add_row(name, file_type, language)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in tables."""
        table_id = event.data_table.id

        if table_id == "voices-table":
            row_key = event.row_key
            if row_key is not None:
                # Get the voice name from the first column
                row_data = event.data_table.get_row(row_key)
                self.selected_voice = str(row_data[0])
                self.log_message(f"Selected voice: {self.selected_voice}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-prepare":
            self.action_prepare_voice()
        elif button_id == "btn-test":
            self.action_test_voice()
        elif button_id == "btn-convert":
            self.action_convert_file()
        elif button_id == "btn-multi":
            self.action_multi_speaker()

    # ========================================================================
    # Actions
    # ========================================================================

    def action_show_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpModal())

    def action_refresh(self) -> None:
        """Refresh all file lists."""
        self.refresh_voices()
        self.refresh_output()
        self.refresh_examples()
        self.log_message("Refreshed file lists")

    def action_prepare_voice(self) -> None:
        """Open prepare voice dialog."""
        def handle_result(result):
            if result:
                audio_path, voice_name, transcription = result
                self.run_prepare_voice(audio_path, voice_name, transcription)

        self.push_screen(PrepareVoiceModal(), handle_result)

    def action_test_voice(self) -> None:
        """Open test voice dialog."""
        if not self.selected_voice:
            # Try to get selected row from table
            table = self.query_one("#voices-table", DataTable)
            if table.cursor_row is not None and self.voices:
                try:
                    row_key = table.get_row_at(table.cursor_row)
                    self.selected_voice = str(row_key[0]) if row_key else None
                except Exception:
                    pass

        if not self.selected_voice:
            self.notify("Please select a voice profile first", severity="warning")
            return

        def handle_result(result):
            if result:
                self.run_test_voice(self.selected_voice, result)

        self.push_screen(TestVoiceModal(self.selected_voice), handle_result)

    def action_convert_file(self) -> None:
        """Open convert file dialog."""
        if not self.voices:
            self.notify("No voice profiles available. Create one first.", severity="warning")
            return

        def handle_result(result):
            if result:
                input_file, voice, output_file, language = result
                self.run_convert_file(input_file, voice, output_file, language)

        self.push_screen(ConvertFileModal(self.voices), handle_result)

    def action_multi_speaker(self) -> None:
        """Open multi-speaker dialog."""
        self.notify("Multi-speaker mode - coming soon!", severity="information")
        self.log_message("Multi-speaker podcast generation")
        self.log_message("Use: python scripts/multi_speaker.py script.txt -o output.mp3")

    # ========================================================================
    # Workers (background tasks)
    # ========================================================================

    @work(exclusive=True, thread=True)
    def run_prepare_voice(self, audio_path: str, voice_name: str, transcription: str) -> None:
        """Run voice preparation in background."""
        self.log_message(f"Preparing voice '{voice_name}' from {audio_path}")
        self.set_status(f"Preparing voice: {voice_name}...")

        cmd = [
            str(VENV_PYTHON), str(SCRIPTS_DIR / "voice_factory.py"),
            "prepare", audio_path, "--name", voice_name
        ]

        if transcription:
            cmd.extend(["--transcription", transcription])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                self.log_message(f"Voice '{voice_name}' prepared successfully", "success")
                self.call_from_thread(self.refresh_voices)
                self.call_from_thread(self.notify, f"Voice '{voice_name}' ready!", severity="information")
            else:
                self.log_message(f"Failed to prepare voice: {result.stderr}", "error")
                self.call_from_thread(self.notify, "Voice preparation failed", severity="error")
        except subprocess.TimeoutExpired:
            self.log_message("Voice preparation timed out", "error")
        except Exception as e:
            self.log_message(f"Error: {e}", "error")

        self.set_status("Ready")

    @work(exclusive=True, thread=True)
    def run_test_voice(self, voice_name: str, text: str) -> None:
        """Run voice test in background."""
        self.log_message(f"Testing voice '{voice_name}'")
        self.log_message(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
        self.set_status(f"Generating test audio for {voice_name}...")

        voice_path = VOICES_DIR / f"{voice_name}.wav"

        cmd = [
            str(VENV_PYTHON), str(SCRIPTS_DIR / "voice_factory.py"),
            "test", str(voice_path), text
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )

            # Log output
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.log_message(line)

            if result.returncode == 0:
                self.log_message(f"Test audio generated: output/test_{voice_name}.wav", "success")
                self.call_from_thread(self.refresh_output)
                self.call_from_thread(self.notify, "Test audio generated!", severity="information")
            else:
                self.log_message(f"Test failed: {result.stderr}", "error")
                self.call_from_thread(self.notify, "Test failed", severity="error")
        except subprocess.TimeoutExpired:
            self.log_message("Test timed out (5 min limit)", "error")
        except Exception as e:
            self.log_message(f"Error: {e}", "error")

        self.set_status("Ready")

    @work(exclusive=True, thread=True)
    def run_convert_file(self, input_file: str, voice: str, output_file: str, language: str) -> None:
        """Run file conversion in background."""
        self.log_message(f"Converting: {input_file}")
        self.log_message(f"Voice: {voice}, Language: {language}")
        self.set_status(f"Converting {Path(input_file).name}...")

        cmd = [
            str(VENV_PYTHON), str(SCRIPTS_DIR / "md_to_audio.py"),
            input_file, "--voice", voice, "--language", language
        ]

        if output_file:
            cmd.extend(["-o", output_file])

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )

            # Stream output to log
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    self.log_message(line.strip())

            process.wait()

            if process.returncode == 0:
                self.log_message("Conversion complete!", "success")
                self.call_from_thread(self.refresh_output)
                self.call_from_thread(self.notify, "Conversion complete!", severity="information")
            else:
                self.log_message("Conversion failed", "error")
                self.call_from_thread(self.notify, "Conversion failed", severity="error")
        except Exception as e:
            self.log_message(f"Error: {e}", "error")

        self.set_status("Ready")


# ============================================================================
# Entry Point
# ============================================================================
def main():
    """Main entry point."""
    app = TTSApp()
    app.run()


if __name__ == "__main__":
    main()
