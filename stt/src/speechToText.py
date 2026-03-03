import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
from pynput import keyboard
from pynput.keyboard import Controller, KeyCode
import threading
import time
import sys
#-------------------------------------------------------------------------------
# Konfiguration
HOTKEY_KEYS = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.ctrl_r}
FS = 16000
MODEL_SIZE = "base"
#-------------------------------------------------------------------------------
class SttTool:
  #-----------------------------------------------------------------------------
  def __init__(self):
    self.kbController = Controller()
    self.currentKeys = set()
    self.recording = False
    self.audioData = []
    self.model = whisper.load_model(MODEL_SIZE)
    self.running = True
  #-----------------------------------------------------------------------------
  def typeText(self, text):
    """Schreibe Text als Tastatureingaben"""
    try:
      cleanText = text.replace("Kommando neue Zeile", "\n").replace("Kommando Neue Zeile", "\n")
      self.kbController.type(cleanText)
    except Exception as e:
      print(f"Fehler beim Tippen: {e}")
  #-----------------------------------------------------------------------------
  def processAudio(self, data):
    """Hintergrund-Thread für KI-Verarbeitung"""
    tempFile = f"temp_{int(time.time())}.wav"
    try:
      fullAudio = np.concatenate(data, axis=0)
      wav.write(tempFile, FS, fullAudio)        
      result = self.model.transcribe(tempFile, language="de")
      text = result["text"].strip()        
      if text:
        # Gehe eine Zeile runter (unter den Pegel) und schreibe Text
        # \033[B = Cursor runter, \r = Zeilenanfang, \033[K = Zeile löschen
        sys.stdout.write(f"\n\r\033[K{text}\033[A\r")
        sys.stdout.flush()
        self.typeText(text)
      else:
        # Falls kein Text erkannt wurde, Zeile unter Pegel löschen
        sys.stdout.write("\n\r\033[K\033[A\r")
        sys.stdout.flush()
    finally:
      if os.path.exists(tempFile):
        os.remove(tempFile)
  #-----------------------------------------------------------------------------
  def drawLevel(self, data):
    """Zeichnet eine einfache Pegelanzeige in die Konsole"""
    if len(data) == 0:
      return
    rms = np.sqrt(np.mean(data.astype(np.float32)**2))
    level = int(rms / 500)
    bar = "█" * min(level, 40)
    # \r = Zeilenanfang, \033[K = Zeile löschen
    sys.stdout.write(f"\r\033[K🎤 [{bar:<40}]")
    sys.stdout.flush()
  #-----------------------------------------------------------------------------
  def recordLoop(self):
    """Audio-Stream Loop"""
    try:
      with sd.InputStream(samplerate=FS, channels=1, dtype='int16') as stream:
        while self.recording and self.running:
          data, _ = stream.read(1024)
          self.audioData.append(data.copy())
          self.drawLevel(data)
    except Exception as e:
      sys.stdout.write(f"\n❌ Fehler im Mikrofon-Thread: {e}\n")
  #-----------------------------------------------------------------------------
  def start(self):
    if not self.recording and self.running:
      # Gehe sicher dass wir in der Pegel-Zeile sind
      # Lösche Pegel-Zeile UND die Text-Zeile darunter
      sys.stdout.write("\r\033[K\n\r\033[K\033[A\r") 
      sys.stdout.flush()
      self.recording = True
      self.audioData = []
      threading.Thread(target=self.recordLoop, daemon=True).start()
  #-----------------------------------------------------------------------------
  def stop(self):
    if self.recording:
      self.recording = False
      dataToProcess = self.audioData[:]
      if dataToProcess and self.running:
        sys.stdout.write("\r\033[K⏳ Verarbeite...\r")
        sys.stdout.flush()
        threading.Thread(target=self.processAudio, args=(dataToProcess,), daemon=True).start()
  #-----------------------------------------------------------------------------
  def onPress(self, key):
    if not self.running:
      return False
    if key in HOTKEY_KEYS:
      self.currentKeys.add(key)
      if all(k in self.currentKeys for k in HOTKEY_KEYS):
        self.start()
  #-----------------------------------------------------------------------------
  def onRelease(self, key):
    if key in HOTKEY_KEYS:
      if key in self.currentKeys:
        self.currentKeys.remove(key)
      if not all(k in self.currentKeys for k in HOTKEY_KEYS):
        self.stop()
#-------------------------------------------------------------------------------
tool = SttTool()
os.system('cls' if os.name == 'nt' else 'clear')
print(f"Bereit. STRG_L+ALT_L+STRG_R gedrückt halten zum Sprechen.")
print("Drücken Sie CTRL+C zum Beenden.\n")
# Platzhalter für die zwei Zeilen (Pegel + Text) schaffen
sys.stdout.write("\n\n\033[2A")
sys.stdout.flush()
try:
  with keyboard.Listener(on_press=tool.onPress, on_release=tool.onRelease) as listener:
    while listener.running:
      time.sleep(0.1)
except KeyboardInterrupt:
  # Cursor ans Ende bewegen für sauberen Exit
  sys.stdout.write("\n\n👋 Programm wird beendet...\n")
  tool.running = False
  tool.stop()
  time.sleep(0.5)
  sys.exit(0)
#-------------------------------------------------------------------------------
