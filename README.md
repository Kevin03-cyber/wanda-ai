# Wanda

A local, private AI assistant with a chat history UI, built with Flask, SQLite and Ollama (Llama 3.2).

> Fan-inspired project, not affiliated with Marvel or Disney.

## Run it
1. Install [Ollama](https://ollama.com) and run `ollama pull llama3.2:3b`
2. `python -m venv venv` then `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `python app.py` and open http://localhost:5004

## Features so far
- Local LLM, no cloud and no API key
- Streaming answers
- Chat history saved in SQLite
- Light and dark theme

## Planned
RAG over your own notes, login with 2FA, prompt-injection defense, CVE lookup.