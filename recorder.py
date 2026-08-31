import sounddevice as sd
import soundfile as sf
import threading
import queue
import subprocess
import re
import shutil
import sys
import os
from datetime import datetime
from openai import OpenAI

DEVICE_NAME = "Aggregate Device"
TARGET_OUTPUT = "Multi-Output Device"
SAMPLE_RATE = 44100
CHANNELS = 4

MLX_WHISPER_PATH = "/Users/ulix/Library/Python/3.9/bin/mlx_whisper"
MLX_MODEL = "mlx-community/whisper-medium-mlx"

OPENAI_MODEL = "gpt-4.1-mini"

PROMPT = """
Analiza esta transcripción de una reunión comercial/preventa.

Genera:
1. Resumen breve
2. Temas tratados
3. Necesidades o dolores del cliente
4. Oportunidades identificadas
5. Siguientes pasos

Ignora ruido, frases repetidas y corrige errores obvios de transcripción cuando el contexto lo permita.
Responde en español, claro y ejecutivo.
"""

audio_queue = queue.Queue()
recording = True

def ensure_audio_output():
    if not shutil.which("SwitchAudioSource"):
        print("No encontré SwitchAudioSource.")
        print("Instálalo con: brew install switchaudio-osx")
        sys.exit(1)

    current_output = subprocess.check_output(
        ["SwitchAudioSource", "-c"],
        text=True
    ).strip()

    print(f"Salida actual: {current_output}")

    if current_output != TARGET_OUTPUT:
        print(f"Cambiando salida a: {TARGET_OUTPUT}")

        result = subprocess.run(
            ["SwitchAudioSource", "-s", TARGET_OUTPUT],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("No pude cambiar la salida de audio.")
            print(result.stderr)
            sys.exit(1)

    final_output = subprocess.check_output(
        ["SwitchAudioSource", "-c"],
        text=True
    ).strip()

    print(f"Salida configurada: {final_output}")

    if final_output != TARGET_OUTPUT:
        print("La salida no quedó en Multi-Output Device.")
        sys.exit(1)

ensure_audio_output()

title = input("Título de la grabación: ").strip()
safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title) or "recording"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

wav_file = f"{safe_title}_{timestamp}.wav"
mp3_file = f"{safe_title}_{timestamp}.mp3"
txt_file = f"{safe_title}_{timestamp}.txt"
summary_file = f"{safe_title}_{timestamp}_summary.txt"

device_id = None

for idx, device in enumerate(sd.query_devices()):
    if DEVICE_NAME.lower() in device["name"].lower():
        device_id = idx
        print(f"Usando dispositivo: {device['name']} ({idx})")
        break

if device_id is None:
    raise Exception("No encontré Aggregate Device")

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    audio_queue.put(indata.copy())

def writer_thread():
    with sf.SoundFile(
        wav_file,
        mode="w",
        samplerate=SAMPLE_RATE,
        channels=CHANNELS
    ) as file:
        while recording or not audio_queue.empty():
            try:
                data = audio_queue.get(timeout=0.5)
                file.write(data)
            except queue.Empty:
                continue

thread = threading.Thread(target=writer_thread)
thread.start()

print("\nGrabando...")
print("Presiona ENTER para detener.\n")

with sd.InputStream(
    samplerate=SAMPLE_RATE,
    device=device_id,
    channels=CHANNELS,
    callback=audio_callback
):
    input()

print("\nDeteniendo grabación...\n")

recording = False
thread.join()

print(f"WAV temporal guardado: {wav_file}")

print("\nConvirtiendo a MP3 y mezclando canales...\n")

conversion = subprocess.run([
    "ffmpeg",
    "-y",
    "-i", wav_file,
    "-filter_complex",
    "pan=stereo|c0=c0+c2|c1=c1+c3",
    "-codec:a", "libmp3lame",
    "-qscale:a", "2",
    mp3_file
])

if conversion.returncode != 0:
    print("Error convirtiendo a MP3")
    sys.exit(1)

print(f"MP3 guardado: {mp3_file}")

try:
    os.remove(wav_file)
    print(f"WAV eliminado: {wav_file}")
except Exception as e:
    print(f"No pude eliminar WAV: {e}")

print("\nIniciando transcripción con MLX Whisper...\n")

if not os.path.exists(MLX_WHISPER_PATH):
    print("No encontré mlx_whisper en:")
    print(MLX_WHISPER_PATH)
    sys.exit(1)

transcription = subprocess.run([
    MLX_WHISPER_PATH,
    mp3_file,
    "--model", MLX_MODEL,
    "--language", "es",
    "--output-format", "txt",
    "--temperature", "0",
    "--condition-on-previous-text", "False",
    "--no-speech-threshold", "0.1",
    "--logprob-threshold", "-2.0"
])

if transcription.returncode != 0:
    print("Error durante la transcripción con MLX Whisper")
    sys.exit(1)

generated_txt = mp3_file.replace(".mp3", ".txt")

if os.path.exists(generated_txt):
    if generated_txt != txt_file:
        os.rename(generated_txt, txt_file)

    print(f"\nTranscripción guardada en: {txt_file}")
else:
    print("No encontré el archivo TXT generado por MLX Whisper")
    sys.exit(1)

print("\nGenerando resumen con OpenAI...\n")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("No encontré OPENAI_API_KEY")
    print('Ejecuta: export OPENAI_API_KEY="tu_api_key"')
    sys.exit(1)

with open(txt_file, "r", encoding="utf-8") as f:
    transcript_text = f.read()

client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": transcript_text}
        ],
        temperature=0.2
    )

    summary = response.choices[0].message.content

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"Resumen guardado en: {summary_file}")

except Exception as e:
    print(f"Error usando OpenAI: {e}")
    sys.exit(1)

print("\nProceso completado.\n")
