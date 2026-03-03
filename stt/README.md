# STT (Sound To Text) Tool

A lightweight Python tool that listens to your microphone while a hotkey is pressed, transcribes the speech using OpenAI's Whisper model, and types the result directly into your active window.

---

## English

### Installation

#### Prerequisites
   - Python 3.8+
   - [FFmpeg](https://ffmpeg.org/) (required by Whisper for audio processing)

#### Setup Environment
   Clone/Copy the project to your desired directory. Open a terminal go into the cloned software repository and run:

##### Windows 11
   ```bash
   python.exe -m pip install --upgrade pip
   python -m venv .venv  
   .venv\Scripts\Activate.ps1
   ```

   ```bash
   pip install -r requirements.txt
   ```
   *Note: On some systems, you might need to install `portaudio` for `sounddevice` to work.*

##### Linux
   ```bash
   python -m venv .venv  
   source .venv/bin/activate
   sudo apt-get update
   sudo apt-get install libportaudio2 portaudio19-dev libasound2-dev ffmpeg

   ```

I am using an ASUS Ascent DX10, so Blackwell architecture. Therefore I have currently to install the latest CUDA build. But you also can use CPU only build, then it is only a bit slower.

   ```bash
   pip3 uninstall torch torchaudio -y
   pip3 install --pre torch torchvision --index-url https://download.pytorch.org/whl/nightly/cu130

   ```
   ```bash
   pip install -r requirementsLinux.txt
   ```

### Usage

1. **Start the tool**:
   Run the provided `src\run_stt.bat` or execute:
   ```bash
   cd src
   python speechToText.py
   ```
2. **Operation**:
   - Press and hold **LEFT CTRL + LEFT ALT + RIGHT CTRL**.
   - Speak while holding the keys. You will see a level meter in the console.
   - Release the keys to stop recording.
   - The tool will transcribe the audio in the background and "type" it into your current cursor position.
   - Saying **"neue Zeile"** will insert a line break.
3. **Exit**:
   - Press `CTRL+C` in the terminal window.

### Architecture

The tool is built with a multi-threaded approach to ensure responsiveness:

- **Main Thread**: Manages the keyboard listener (`pynput`) and coordinates state.
- **Microphone Thread**: Handles real-time audio streaming from the soundcard using `sounddevice`.
- **Worker Thread**: Triggered on hotkey release; handles the heavy lifting of Whisper transcription in the background so the UI/listener doesn't freeze.
- **UI/Output**: Uses ANSI escape codes for a clean, two-line console interface (Level meter + Transcription).

