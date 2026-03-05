aiTools — small audio / assistant utilities
=========================================

Brief descriptions of the subprojects in this workspace:

- **assistent**: A small assistant application that provides keyboard-driven automation and voice-related helper functions. See [assistent](assistent/README.md).
- **chatterbox**: Tools for generating long German voice output; includes scripts to synthesize and play speech. See [chatterbox](chatterbox/README.md).
- stt: **Speech To Text  / Push To Talk** utilities including a live hotkey-driven recorder that transcribes audio using Whisper. It inserts the transcription in the current active window. See [stt](stt/README.md).

Quick start
-----------

Each subproject has its own requirements and usage notes. Enter the subproject directory and follow the README there, for example:

```
cd stt
source .venv/bin/activate
pip install -r requirements.txt
python3 src/speechToText.py
```

Notes
-----
- On Ubuntu you may need system packages for audio and media handling, for example: `libportaudio2`, `portaudio19-dev`, `libasound2-dev`, and `ffmpeg`.
- GPU acceleration for Whisper/torch requires a CUDA-compatible PyTorch build; see the project READMEs for details.

License
-------
See the `LICENSE` files in each subproject.

