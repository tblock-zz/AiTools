import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
from pynput import keyboard
from pynput.keyboard import Controller
import threading
import time
import sys
#-------------------------------------------------------------------------------
# Konfiguration
HOTKEY_KEYS = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.ctrl_r}
FS = 16000
MODEL_SIZE = "large-v3"
DEVICE = "cuda"  # oder "cuda" für GPU
COMPUTE_TYPE = "int8"  # int8 für CPU/geringeren RAM, float16 für GPU
#-------------------------------------------------------------------------------
class SttTool:
  #---------------------------------------------------------------------------
  def __init__(self):
    self.kbController = Controller()
    self.currentKeys = set()
    self.recording = False
    self.audioData = []
    self.model = whisper.load_model(MODEL_SIZE, DEVICE)
    self.running = True
    self.lock = threading.Lock()  # Lock für Thread-Sicherheit
    self.level_line_active = False
    self.typing_lock = threading.Lock()
  #---------------------------------------------------------------------------
  def typeText(self, text):
    """Schreibe Text als Tastatureingaben"""
    try:
      # Sicherstellen, dass Level-Zeile nicht stört
      if self.level_line_active:
        # Cursor auf Anfang der Textzeile bringen, gesamte Zeile leeren (2K)
        sys.stdout.write('\033[B\r\033[2K')
        self.level_line_active = False
        
      cleanText = text.replace("Kommando neue Zeile", "\n").replace("Kommando Neue Zeile", "\n")
        
      # Nur einmal schreiben
      #sys.stdout.write(f'\033[K{cleanText}\n')
      #sys.stdout.flush()
      with self.typing_lock:  # Wichtig!
        # Kurze Pause, damit keine Tasten-Überlappung
        time.sleep(0.05)
        # Zeichen einzeln tippen mit minimaler Pause, um Buchstabendreher zu vermeiden
        for char in cleanText:
          self.kbController.type(char)
          time.sleep(0.004)
    except Exception as e:
      print(f"Fehler beim Tippen: {e}")
  #---------------------------------------------------------------------------
  def processAudio(self, data):
    """Hintergrund-Thread für KI-Verarbeitung"""
    tempFile = f"temp_{int(time.time())}.wav"
    try:
      fullAudio = np.concatenate(data, axis=0)
      wav.write(tempFile, FS, fullAudio)
      #audio = whisper.load_audio(tempFile)
      result = self.model.transcribe(tempFile)
      text = result["text"].strip()
        
      if text:
        self.typeText(text)
      else:
        # Falls kein Text erkannt wurde
        with self.lock:
          # Gesamte Zeile leeren (2K)
          sys.stdout.write('\r\033[2K\n')
          sys.stdout.flush()
    finally:
      if os.path.exists(tempFile):
        os.remove(tempFile)
  #---------------------------------------------------------------------------
  def drawLevel(self, data):
    """Zeichnet eine einfache Pegelanzeige in die Konsole"""
    with self.lock:
      if len(data) == 0:
        return
      rms = np.sqrt(np.mean(data.astype(np.float32)**2))
      # Pegel deutlich sensibler machen (Teiler verringert)
      level = int(rms / 50) 
      bar = "█" * min(level, 40)        
      # Cursor bleibt in derselben Zeile und löscht diese vorher komplett (2K)
      sys.stdout.write(f'\r\033[2K🎤 [{bar:<40}]')
      self.level_line_active = True
      sys.stdout.flush()
  #---------------------------------------------------------------------------
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
  #---------------------------------------------------------------------------
  def start(self):
    if not self.recording and self.running:
      with self.lock:
        # Sauberer Start: Zeilen vorbereiten
        sys.stdout.write('\n\033[2K')  # Neue Zeile, löschen
        sys.stdout.write('\033[2K')    # Zweite Zeile löschen
        sys.stdout.write('\033[2A\r') # Zurück zum Anfang
        sys.stdout.flush()
            
      self.recording = True
      self.audioData = []
      threading.Thread(target=self.recordLoop, daemon=True).start()
  #---------------------------------------------------------------------------
  def stop(self):
    if self.recording:
      self.recording = False
      dataToProcess = self.audioData[:]
    
      if dataToProcess and self.running:
        with self.lock:
          # Gesamte Zeile leeren (2K)
          sys.stdout.write('\r\033[2K⏳ Verarbeite...\r')
          sys.stdout.flush()
        
        threading.Thread(target=self.processAudio, args=(dataToProcess,), daemon=True).start()    
  #---------------------------------------------------------------------------
  def onPress(self, key):
    if not self.running:
      return False
    if key in HOTKEY_KEYS:
      self.currentKeys.add(key)
      if all(k in self.currentKeys for k in HOTKEY_KEYS):
        self.start()
  #---------------------------------------------------------------------------
  def onRelease(self, key):
    if key in HOTKEY_KEYS:
      if key in self.currentKeys:
        self.currentKeys.remove(key)
      if not all(k in self.currentKeys for k in HOTKEY_KEYS):
        self.stop()
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  tool = SttTool()
  os.system('cls' if os.name == 'nt' else 'clear')
  print(f"Bereit. STRG_L+ALT_L+STRG_R gedrückt halten zum Sprechen.")
  print("Drücken Sie CTRL+C zum Beenden.\n")
    
  # Zwei leere Zeilen für Pegel und Text reservieren
  sys.stdout.write('\n\n')
  sys.stdout.flush()
    
  try:
    with keyboard.Listener(on_press=tool.onPress, on_release=tool.onRelease) as listener:
      while listener.running:
        time.sleep(0.1)
  except KeyboardInterrupt:
    # Sauberer Exit
    sys.stdout.write("\n\n👋 Programm wird beendet...\n")
    tool.running = False
    tool.stop()
    time.sleep(0.5)
    sys.exit(0)
