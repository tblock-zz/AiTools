"""
This programm 
- records audio from the system audio input device 
- converts it to text
- sends it to an LLM
- converts the LLM text back to audio and plays it
"""
#-------------------------------------------------------------------------------
# tested on Ubuntu 20.04
# use repositoryies and packages:
# whisper:  https://github.com/openai/whisper/tree/main
# bark:     https://huggingface.co/suno/bark
# sounddev: https://readthedocs.org/projects/python-sounddevice/downloads/pdf/latest/
# miniconda:https://docs.conda.io/en/latest/miniconda.html
# Llama2
# obabooga
# other packages
#sudo apt update && sudo apt install ffmpeg
# pip install sounddevice soundfile scipy TTS requests pynput whisper-openai pyperclip
#-------------------------------------------------------------------------------
# if True, the LLM is used
useWebLlm = True
# if True use audio output with bark
useAudioOut = True

autoDetectLanguage = False
tempAudioFile = "./audio.wav"
textFile = "recordedTextOutput.txt"
frequency = 44100
#-------------------------------------------------------------------------------
voicePreset = "v2/de_speaker_3"
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
import os, time
if useAudioOut:
  from scipy.io.wavfile import write
import whisper
import threading
from queue import Queue
from pynput.keyboard import Key, Listener
import tempfile
import argparse
import sounddevice as sd
import soundfile as sf
import pyperclip 
#-------------------------------------------------------------------------------
history = []
#-------------------------------------------------------------------------------
def clearHistory():
  global history
  print("clearing history")
  history = []
#-------------------------------------------------------------------------------
# handling of key presses
#-------------------------------------------------------------------------------
q = Queue()
q2 = Queue()
pressedKeys = set()
#-------------------------------------------------------------------------------
def onKeyPress(key):
  global pressedKeys
  pressedKeys.add(key)
  
  # Check for combination: CTRL_L + SHIFT_L + CTRL_R
  combination = {Key.ctrl_l, Key.shift_l, Key.ctrl_r}
  if all(k in pressedKeys for k in combination):
    q.put("start")
  elif key == Key.ctrl_r:
    clearHistory()
#-------------------------------------------------------------------------------
def onKeyRelease(key):
  global pressedKeys
  
  # If any key of the combination is released, stop recording
  if key in {Key.ctrl_l, Key.shift_l, Key.ctrl_r}:
    q.put("stop")
    
  if key == Key.esc:
    print('Aufnahme beendet')
    q.put("exit")
    return False
    
  if key in pressedKeys:
    pressedKeys.remove(key)
#-------------------------------------------------------------------------------
def runKeyListener():
  with Listener(on_press=onKeyPress, on_release=onKeyRelease) as listener:
    listener.join()
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def audioCallback(indata, frames, time, status):
  if status:
    print(status, file=sys.stderr)
  q2.put(indata.copy())
#-------------------------------------------------------------------------------
# audio recording
#-------------------------------------------------------------------------------
def recordAudio(filename):
  with sf.SoundFile(filename, mode='x', samplerate=frequency,
                    channels=1) as file:
    with sd.InputStream(samplerate=frequency, channels=1, callback=audioCallback):
      while True:
        if not q2.empty():
          file.write(q2.get())
        if not q.empty():
          message = q.get()
          if message == "stop":
            return True
          elif message == "exit":            
            return False
#-------------------------------------------------------------------------------
# audio to text
#-------------------------------------------------------------------------------
def evaluateAudio(model) -> str:
  audio = whisper.load_audio(tempAudioFile)
  audio = whisper.pad_or_trim(audio)
  mel = whisper.log_mel_spectrogram(audio).to(model.device)
  if autoDetectLanguage:
    _, probs = model.detect_language(mel)
    print(f"Detected language: {max(probs, key=probs.get)}")
    options = whisper.DecodingOptions()
  else:
    options = whisper.DecodingOptions(language="de", without_timestamps=True)
  return whisper.decode(model, mel, options).text
#-------------------------------------------------------------------------------
# text to audio
#-------------------------------------------------------------------------------
from bark import SAMPLE_RATE, generate_audio, preload_models
def initWavOutput():
  preload_models()
#-------------------------------------------------------------------------------
def createWav(text: str):
  audioArray = generate_audio(text, history_prompt=voicePreset)
  write("bark.wav", SAMPLE_RATE, audioArray)
#-------------------------------------------------------------------------------
def playWav():
  filename = 'bark.wav'
  data, fs = sf.read(filename, dtype='float32')  
  sd.play(data, fs)
  sd.wait() 
#-------------------------------------------------------------------------------
# sending text to LLM and retrieve response
#-------------------------------------------------------------------------------
if useWebLlm:
  import requests
  url = "http://127.0.0.1:11434/v1/chat/completions"
#-------------------------------------------------------------------------------
def sendMessage(prompt: str, historyList, modelName):
  if useWebLlm:
    data = {
      "model": modelName,
      "messages": historyList + [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, json=data)
    try:
      message = response.json()['choices'][0]['message']['content']
    except Exception as e:
      print("Fehler beim Parsen der Ollama-Antwort:", e)
      print("Antwort:", response.text)
      message = response.text
    return message
  else:
    return prompt
#-------------------------------------------------------------------------------
def debugPrint(content):
  strTime = round(time.time(), 2)
  print(f"[{strTime}]", content)
#-------------------------------------------------------------------------------
# argument parsing
#-------------------------------------------------------------------------------
def parseArgs():
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument(
    "-h", "--help",
    action="store_true",
    help="Zeigt die Hilfe-Nachricht an"
  )
  parser.add_argument(
    "--plain",
    action='store_true',
    help="Use plain implementation"
  )
  parser.add_argument(
    "-m", "--model",
    type=str,
    default="gemma3",
    help="Ollama model name (default: gemma3)"
  )
  
  args = parser.parse_args()
  
  if args.help:
    helpText = f"""
Bedienung:
- Aufnahme starten:   CTRL_L + SHIFT_L + LEFT (gedrückt halten)
- Aufnahme stoppen:    Eine der Tasten loslassen
- Programm beenden:   ESC

Genutztes Modell: {args.model}

Argumente:
-h, --help            Zeigt diese Hilfe an
-m, --model MODEL     Ollama Modellname (Standard: gemma3)
--plain               Nutze Plain-Implementierung
    """
    print(helpText)
    exit()
    
  return args
#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
def main():
  global history
  args = parseArgs()
  if useAudioOut:
    initWavOutput()
  print(f"""Starte die Aufname mit CTRL_LEFT + SHIFT_LEFT + LEFT.
  Die Aufnahme stoppt, wenn eine der Tasten losgelassen wird.
  Programmende mit ESC.
  Genutztes Modell: {args.model}""")
  listenerThread = threading.Thread(target=runKeyListener)
  listenerThread.start()
  
  debugPrint("Loading Whisper model...")
  model = whisper.load_model("base")
  outputFile = open(textFile, "w")
  debugPrint("starting")
  doRun = True
  while doRun:
    if not q.empty():
      queueMessage = q.get()
      if queueMessage == "start":
        debugPrint(f"recording...")
        if os.path.isfile(tempAudioFile):
          os.remove(tempAudioFile)
        doRun = recordAudio(tempAudioFile)
        debugPrint("recording finished, evaluating...")
        generatedText = evaluateAudio(model)
        debugPrint("")
        print(generatedText)
        pyperclip.copy(generatedText)
        outputFile.write(generatedText + "\n")
        if args.plain is False:
          responseMessage = sendMessage(generatedText, history, args.model)
          history.append({"role": "assistant", "content": responseMessage})
          debugPrint("")
          print(responseMessage)
        if useAudioOut:
          createWav(responseMessage)
          playWav()
      elif queueMessage == "exit":
        doRun = False
  outputFile.close()
  exit()
#-------------------------------------------------------------------------------
if __name__ == "__main__":
  main()
