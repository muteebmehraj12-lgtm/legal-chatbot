import streamlit as st
from openai import OpenAI
import json
import os
import pdfplumber
import base64
import uuid
import io
from cryptography.fernet import Fernet

def get_chat_file(user_id):
    return f"chat_{user_id}.json"

def load_messages(user_id):
    filename = get_chat_file(user_id)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return []

def save_messages(user_id, messages):
    with open(get_chat_file(user_id), "w") as f:
        json.dump(messages, f)

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()

def transcribe_audio_bytes(client, audio_bytes):
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "mic_audio.wav"
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="gpt-4o-mini-transcribe"
    )
    return transcript.text

def speak_text(client, text):
    audio = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )
    return audio.read()

def get_encryption_key():
    if "enc_key" not in st.session_state:
        st.session_state.enc_key = Fernet.generate_key()
    return st.session_state.enc_key

def encrypt_text(text):
    f = Fernet(get_encryption_key())
    return f.encrypt(text.encode()).decode()

def decrypt_text(token):
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(token.encode()).decode()
    except Exception:
        return token

st.set_page_config(page_title="Legal AI Chatbot", page_icon="⚖️")

st.markdown("""
⚠️ **Disclaimer**  
This chatbot provides **general legal information only**.  
It does **not** constitute legal advice.  
Consult a qualified legal professional for advice.
""")

st.markdown(
    "🧩 **Features:** Context-aware chat · PDF analysis · Voice input · Spoken responses"
)

st.caption("🔐 Stored conversations are encrypted for privacy.")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

query_params = st.experimental_get_query_params()

if "user_id" in query_params:
    st.session_state.user_id = query_params["user_id"][0]
else:
    st.session_state.user_id = str(uuid.uuid4())
    st.experimental_set_query_params(user_id=st.session_state.user_id)

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(st.session_state.user_id)

st.markdown("## ⚖️ Legal Assistant")

uploaded_file = st.file_uploader(
    "Upload a legal document (PDF)",
    type=["pdf"]
)

audio_file = st.file_uploader(
    "Upload a voice question (WAV or MP3)",
    type=["wav", "mp3"]
)

audio_bytes = st.audio_input("🎤 Speak (experimental)")

document_text = ""

if uploaded_file:
    document_text = extract_text_from_pdf(uploaded_file)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(decrypt_text(msg["content"]))

user_input = st.chat_input("Ask a legal question...")

if audio_bytes:
    user_input = transcribe_audio_bytes(client, audio_bytes)

if audio_file:
    user_input = transcribe_audio_bytes(client, audio_file.read())

if document_text and user_input:
    user_input = (
        "The user uploaded a legal document:\n\n"
        f"{document_text}\n\n"
        f"Question: {user_input}"
    )

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": encrypt_text(user_input)
    })
    save_messages(st.session_state.user_id, st.session_state.messages)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal information assistant. "
                "Provide general legal information only. "
                "Do not give legal advice."
            )
        }
    ]

    for msg in st.session_state.messages:
        messages.append({
            "role": msg["role"],
            "content": decrypt_text(msg["content"])
        })

    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        st.markdown(reply)
        st.audio(speak_text(client, reply), format="audio/mp3")

    st.session_state.messages.append({
        "role": "assistant",
        "content": encrypt_text(reply)
    })
    save_messages(st.session_state.user_id, st.session_state.messages)
