# KI-Assistent (Voice-to-Text & LLM Interface)

Dieser Assistent ermöglicht eine Sprachsteuerung, die ähnlich wie Alexa oder Siri funktioniert, jedoch lokal läuft. Er kombiniert Spracherkennung (STT), ein lokales Sprachmodell (LLM) und optionale Sprachausgabe (TTS).

## Architektur & Funktionsweise

Der Assistent folgt einem modularen Datenfluss:

1.  **Audio-Aufnahme**: Mittels `sounddevice` wird Audio vom System-Input aufgenommen, sobald die definierte Tastenkombination gedrückt wird.
2.  **Spracherkennung (STT)**: Die Aufnahme wird als temporäre WAV-Datei gespeichert und durch OpenAI's `Whisper`-Modell in Text umgewandelt.
3.  **Clipboard-Integration**: Der erkannte Text wird automatisch in die System-Zwischenablage kopiert (`pyperclip`).
4.  **LLM-Verarbeitung**: Der Text wird an eine lokale Ollama-Instanz gesendet. Dabei wird ein Gesprächsverlauf (History) mitgeführt, um kontextbezogene Antworten zu ermöglichen.
5.  **Sprachausgabe (TTS)**: Die Antwort des LLM kann optional über das `Bark`-Modell wieder in Sprache umgewandelt und abgespielt werden.

## Features

- **Lokale Ausführung**: Alle Komponenten (Whisper, Ollama, Bark) laufen lokal auf dem Rechner.
- **Hotkey-Steuerung**: Einfache Bedienung über systemweite Tastenkombinationen.
- **Kontext-Bewusstsein**: Speichert den Verlauf der aktuellen Sitzung.
- **Flexibilität**: Verschiedene LLM-Modelle über Ollama ansteuerbar.

## Voraussetzungen

### Hardware & Software
- **Python 3.10+**
- **FFmpeg**: Erforderlich für die Audioverarbeitung (Whisper).
- **Ollama**: Muss lokal installiert sein und laufen (Standard-Port 11434).

### Lokale Modelle
- **Whisper**: Das "base"-Modell wird beim ersten Start automatisch geladen.
- **Ollama Modell**: Standardmäßig wird `gemma3` erwartet (kann per Parameter geändert werden).
- **Bark (Optional)**: Für die Sprachausgabe. Der Code importiert und nutzt `bark`, wenn `useAudioOut=True`. Bark benötigt die entsprechenden Modelle (z. B. von HuggingFace) und kann GPU-Beschleunigung für sinnvoll schnelle TTS-Ausgabe erfordern.

## Installation

1.  Klone das Repository.
2.  Installiere die Abhängigkeiten:
    ```bash
    pip install -r requirements.txt
    ```
3.  Stelle sicher, dass Ollama gestartet ist und das gewünschte Modell geladen wurde:
    ```bash
    ollama run gemma3
    ```

## Bedienung

Das Programm wird über die Kommandozeile gestartet und reagiert auf folgende Tasten:

| Aktion | Tastenkombination |
| :--- | :--- |
| **Aufnahme starten** | `CTRL_L` + `SHIFT_L` + `LEFT` (gedrückt halten) |
| **Aufnahme stoppen** | Eine der Tasten loslassen |
| **Programm beenden** | `ESC` |
| **History löschen** | `CTRL_R` |

## Kommandozeilenparameter

```bash
python assistent.py [Optionen]
```

- `-m, --model MODEL`: Name des Ollama-Modells (Standard: `gemma3`).
- `--plain`: Nutzt nur die Spracherkennung (Text in Clipboard), ohne das LLM anzufragen.
- `-h, --help`: Zeigt die Hilfe an.

## Konfiguration im Code

In der Datei `assistent.py` können folgende Parameter angepasst werden:
- `useWebLlm`: LLM-Nutzung aktivieren (Default: `True`).
- `useAudioOut`: Aktiviert/Deaktiviert die Sprachausgabe via Bark (Default: `True`).
- `autoDetectLanguage`: Automatische Spracherkennung vs. fest eingestellt auf Deutsch (Default: `False`).
- `voicePreset`: Bestimmt die Stimme für die Bark-Ausgabe.
