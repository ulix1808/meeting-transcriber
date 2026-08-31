# meeting-transcriber

Graba reuniones en macOS, las transcribe localmente con MLX Whisper y genera un resumen ejecutivo con OpenAI.

Todo el audio se procesa en la máquina local: solo el texto de la transcripción se envía a OpenAI para el resumen.

## Cómo funciona

1. Captura el audio del sistema y del micrófono a través de un Aggregate Device de macOS.
2. Guarda un WAV temporal de 4 canales mientras grabas.
3. Al terminar, mezcla los canales y convierte a MP3 con `ffmpeg`.
4. Transcribe el MP3 con MLX Whisper (local, optimizado para Apple Silicon).
5. Genera un resumen de reunión comercial con la API de OpenAI.

Salidas por grabación: `<titulo>_<timestamp>.mp3`, `.txt` y `_summary.txt`.

## Requisitos

- macOS con Apple Silicon
- Python 3.9+
- [`ffmpeg`](https://ffmpeg.org/) y `switchaudio-osx`:

```bash
brew install ffmpeg switchaudio-osx
```

- MLX Whisper:

```bash
pip3 install --user mlx-whisper
```

- Dependencias de Python:

```bash
pip3 install -r requirements.txt
```

## Configuración de audio

En **Audio MIDI Setup** de macOS crea:

- Un **Aggregate Device** que combine tu micrófono y un dispositivo de loopback (BlackHole, Loopback, etc.) para capturar también el audio del sistema.
- Un **Multi-Output Device** para seguir escuchando mientras se graba.

El script cambia automáticamente la salida al Multi-Output Device antes de empezar.

Si tus dispositivos tienen otros nombres, ajusta las constantes al inicio de `recorder.py`:

```python
DEVICE_NAME = "Aggregate Device"
TARGET_OUTPUT = "Multi-Output Device"
```

`MLX_WHISPER_PATH` también apunta a una ruta local y probablemente necesites cambiarla.

## Uso

Copia `.env.example` a `.env` y pon tu API key:

```bash
cp .env.example .env
```

Luego:

```bash
./recorder.sh
```

Te pedirá un título, empezará a grabar y se detendrá cuando presiones ENTER.

## Transcribir un archivo existente

Para un audio que ya tienes (por ejemplo, una nota de voz):

```bash
ffmpeg -i entrada.m4a -codec:a libmp3lame -qscale:a 2 salida.mp3

mlx_whisper salida.mp3 \
  --model mlx-community/whisper-medium-mlx \
  --language es \
  --output-format txt \
  --temperature 0 \
  --condition-on-previous-text False
```

## Nota

Los audios, transcripciones y resúmenes están en `.gitignore`: suelen contener información confidencial de reuniones y no deben subirse al repositorio.
