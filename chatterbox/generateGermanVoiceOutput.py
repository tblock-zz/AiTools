#  (New-Object Media.SoundPlayer "d:\1.user\tom\projects\prg\python\ai\audio\chatterbox\audioOutput.wav").PlaySync()
# python -m venv C:\projects\venv\chatterbox
# C:\projects\venv\chatterbox\Scripts\Activate.ps1
# pip install chatterbox pyaudio keyboard numpy torch torchaudio
# python generateGermanVoiceOutput.py
# using https://huggingface.co/ResembleAI/chatterbox-turbo
# ------------------------------------------------------------------------------
import argparse
import sys, re, os, pathlib
import wave
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.tts_turbo import ChatterboxTurboTTS
import torch
import torchaudio as ta
import pyaudio
import time
import keyboard
import numpy as np
import math
# ------------------------------------------------------------------------------
def timerDecorator(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()        
        print(f"\nFunktion '{func.__name__}' dauerte {end - start:.4f}s")
        return result
    return wrapper
# ------------------------------------------------------------------------------
def getArguments():
  parser = argparse.ArgumentParser(
    description="Generiert deutsche Sprachausgabe aus Text oder einer Datei.",
    add_help=True
  )
  parser.add_argument(
    "-t", "--text", 
    help="Direkter Text für die Sprachausgabe (in Anführungszeichen)"
  )
  parser.add_argument(
    "-f", "--file", 
    help="Pfad zu einer Textdatei, deren Inhalt vorgelesen werden soll"
  )
  parser.add_argument(
    "-w", "--wav", 
    help="Pfad zu der Beispiel Stimmdatei im wav Format."
  )
  parser.add_argument(
    "-r", "--record",
    action="store_true",
    help="Nimmt Audio vom Mikrofon auf solange shift gedrückt ist, um es als Sprachvorlage zu verwenden."
  )
  return parser.parse_args()
# ------------------------------------------------------------------------------
def getCurrentWorkingDirectory():
  return os.getcwd()
# ------------------------------------------------------------------------------
def getTextFromInput(args):
  if args.text:
    return args.text
  if args.file:
    try:
      with open(args.file, "r", encoding="utf-8") as fileHandle:
        return fileHandle.read().strip()
    except Exception as error:
      print(f"Fehler beim Lesen der Datei: {error}")
      sys.exit(1)
  return None
# ------------------------------------------------------------------------------
def countSyllables(text):
    """
    Schätzt die Silbenanzahl im Deutschen.
    Zählt Vokalgruppen (z.B. 'au', 'ei', 'ie' zählen als eine Silbe).
    """
    # Heuristik: Jede Gruppe von Vokalen entspricht in der Regel einer Silbe
    vowel_groups = re.findall(r'[aeiouyäöü]+', text.lower())
    return len(vowel_groups)
# ------------------------------------------------------------------------------
def splitTextIntoChunks(text, target_syllables=100):
    """
    Teilt Text in Sätze und gruppiert diese in Chunks mit 
    annähernd gleicher Silbenanzahl.
    """
    print(f"Text in Abschnitte aufteilen (Ziel: ca. {target_syllables} Silben pro Chunk)...")   
    # 1. In Sätze splitten (behält Satzzeichen bei)
    sentence_pattern = r'(?<=[.:!?])\s+'
    sentences = [s.strip() for s in re.split(sentence_pattern, text.strip()) if s.strip()]    
    
    chunks = []
    current_chunk = []
    current_syllables = 0
    
    for sentence in sentences:
        s_count = countSyllables(sentence)
        
        # Falls der Chunk bereits Inhalt hat und der neue Satz das Limit überschreiten würde:
        # Chunk abschließen und neuen beginnen.
        if current_chunk and (current_syllables + s_count > target_syllables):
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_syllables = s_count
        else:
            current_chunk.append(sentence)
            current_syllables += s_count            
    # Letzten Chunk hinzufügen
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks
# ------------------------------------------------------------------------------
def initializeModel(deviceType):
  return ChatterboxMultilingualTTS.from_pretrained(device=deviceType)
# ------------------------------------------------------------------------------
def generateAudio(multilingualModel, textToSpeak, voicePromptPath):
  languageId = "de"
  return multilingualModel.generate(
    text=textToSpeak, 
    language_id=languageId, 
    audio_prompt_path=voicePromptPath
  )
# ------------------------------------------------------------------------------
def generateAudioTurbo(model, textToSpeak, voicePromptPath):
  wav = model.generate(textToSpeak, audio_prompt_path=voicePromptPath)
  return wav
# ------------------------------------------------------------------------------
def calculateRms(audioData):
  audioArray = np.frombuffer(audioData, dtype=np.int16)
  if len(audioArray) == 0:
    return 0.0
  squareSum = np.sum(audioArray.astype(np.float64)**2)
  return np.sqrt(squareSum / len(audioArray))
# ------------------------------------------------------------------------------
def displayLevelMeter(rmsValue, maxRms=32767.0, barLength=40):
  normalizedLevel = min(rmsValue / (maxRms / 10), 1.0)
  filledLength = int(barLength * normalizedLevel)
  bar = "#" * filledLength + "-" * (barLength - filledLength)
  sys.stdout.write(f"\rPegel: [{bar}] {rmsValue:6.1f}")
  sys.stdout.flush()
# ------------------------------------------------------------------------------
def recordAudio(filename, chunkSize=1024, sampleFormat=pyaudio.paInt16, channelCount=1, samplingRate=44100):
  pAudio = pyaudio.PyAudio()
  audioStream = None
  try:
    print("Halte die SHIFT-Taste gedrückt, um die Aufnahme zu starten...")
    keyboard.wait('shift')
    print("Aufnahme läuft... (Lasse SHIFT los zum Beenden)")
    audioStream = pAudio.open(
      format=sampleFormat,
      channels=channelCount,
      rate=samplingRate,
      frames_per_buffer=chunkSize,
      input=True
    )
    audioFrames = []
    while keyboard.is_pressed('shift'):
      audioData = audioStream.read(chunkSize)
      audioFrames.append(audioData)
      rmsValue = calculateRms(audioData)
      displayLevelMeter(rmsValue)
    print("\n")
    saveWavFile(filename, audioFrames, pAudio, sampleFormat, channelCount, samplingRate)
  finally:
    if audioStream is not None:
      audioStream.stop_stream()
      audioStream.close()
    pAudio.terminate()
    print("Aufnahme beendet.")
# ------------------------------------------------------------------------------
def saveWavFile(filename, frames, pAudio, sampleFormat, channelCount, samplingRate):
  with wave.open(filename, 'wb') as wavFile:
    wavFile.setnchannels(channelCount)
    wavFile.setsampwidth(pAudio.get_sample_size(sampleFormat))
    wavFile.setframerate(samplingRate)
    wavFile.writeframes(b''.join(frames))
# ------------------------------------------------------------------------------
def wavMergeStandard(file_list, output_path):
    data = []
    params = None    
    for file in file_list:
        with wave.open(file, 'rb') as w:
            if params is None:
                params = w.getparams()
            data.append(w.readframes(w.getnframes()))
    with wave.open(output_path, 'wb') as w:
        w.setparams(params)
        for frame in data:
            w.writeframes(frame)
# ------------------------------------------------------------------------------
@timerDecorator
def runMain():
  args = getArguments()
  if args.record:
    pathWavMyVoice = "recordedSample.wav"
    recordAudio(pathWavMyVoice)
    exit()
  textForVoiceGeneration = getTextFromInput(args)
  if not textForVoiceGeneration:
    print("Fehler: Bitte geben Sie Text mit -t oder eine Datei mit -f an.")
    print("Nutzen Sie -h oder --help für weitere Informationen.")
    sys.exit(1)
  deviceType = "cuda"
  pathWavMyVoice = args.wav if args.wav else pathlib.Path(getCurrentWorkingDirectory()) / "recordedSample.wav"
  audioData = []
  chunks = splitTextIntoChunks(textForVoiceGeneration)
  multilingualModel = initializeModel(deviceType)
  #modelTurbo = ChatterboxTurboTTS.from_pretrained(device="cuda")
  for i, chunk in enumerate(chunks):
      print(f"--- Generiere Audio für Abschnitt {i+1}/{len(chunks)}...")
      audioWavChunk = generateAudio(multilingualModel, chunk, pathWavMyVoice)
      #audioWavChunk = generateAudioTurbo(modelTurbo, chunk, pathWavMyVoice)
      audioData.append(audioWavChunk)
  # concatenate all audio chunk wav files into one final output wav file
  combinedWaveform = torch.cat(audioData, dim=1)
  ta.save("audioGenerated.wav", combinedWaveform, multilingualModel.sr)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
  runMain()
