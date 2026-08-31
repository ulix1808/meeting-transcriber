#!/bin/zsh

cd "$(dirname "$0")"

if [[ -f .env ]]; then
  source .env
fi

if [[ -z "$OPENAI_API_KEY" ]]; then
  echo "Falta OPENAI_API_KEY."
  echo 'Ponla en un archivo .env con: export OPENAI_API_KEY="tu_api_key"'
  exit 1
fi

python3 recorder.py
