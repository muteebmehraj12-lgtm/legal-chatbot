import streamlit as st
from openai import OpenAI
import json
import os
import pdfplumber
import base64
import uuid
import io
import base64
import uuid
import jwt

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

st.markdown("## 🔐 Sign in with Google")

google_token = st.text_input(
    "Paste Google ID token",
    help="Sign in using Google OAuth token"
)

if not google_token:
    st.stop()

user_info = jwt.decode(
    google_token,
    options={"verify_signature": False}
)

st.success(f"Logged in as {user_info['email']}")
st.session_state.user_id = user_info["email"]

try:
    user_info = jwt.decode(
        google_token,
        options={"verify_signature": False}
    )
except Exception:
    st.error("Invalid Google token")
    st.stop()

st.success(f"Logged in as {user_info['email']}")

st.session_state.user_id = user_info["email"]


def transcribe_audio_bytes(client, audio_bytes):
    transcript = client.audio.transcriptions.create(
        file=audio_bytes,
        model="gpt-4o-mini-transcribe"
    )
    return transcript.text

st.markdown("""
⚠️ **Disclaimer**  
This chatbot provides **general legal information only**.  
It does **not** constitute legal advice and is **not a substitute** for a qualified lawyer.  
For advice specific to your situation, please consult a licensed legal professional.
""")

st.markdown(
    "🧩 **Features:** Context-aware chat · PDF analysis · Image understanding · Voice input · Spoken responses"
)

st.info("Google Sign-In will be enabled shortly.")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


if "messages" not in st.session_state:
    st.session_state.messages = load_messages(st.session_state.user_id)

st.markdown("## ⚖️ Legal Assistant")

uploaded_file = st.file_uploader(
    "Upload a legal document (image or PDF)",
    type=["png", "jpg", "jpeg", "pdf"]
)

audio_file = st.file_uploader(
    "Upload a voice question (WAV or MP3)",
    type=["wav", "mp3"]
)
st.caption(
    "You can ask questions by typing, uploading a voice recording, or speaking via the microphone if supported by your browser."
)
st.caption("🔐 Stored conversations are encrypted for privacy.")


document_text = ""
image_bytes = None

if uploaded_file is not None:
    st.info("Document uploaded successfully.")
    if uploaded_file.type == "application/pdf":
        document_text = extract_text_from_pdf(uploaded_file)
    else:
        image_bytes = uploaded_file.getvalue()
        
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(decrypt_text(msg["content"]))


user_input = st.chat_input("Ask a legal question or refer to the uploaded document...")
audio_bytes = st.audio_input("🎤 Speak (experimental – may show warnings)")



if audio_bytes is not None:
    user_input = transcribe_audio_bytes(client, audio_bytes)
    st.info(f"Transcribed voice input: {user_input}")


if audio_file:
    user_input = transcribe_audio(client, audio_file)
    st.info("Audio input transcribed.")

if document_text and user_input:
    user_input = (
        "The user has uploaded a legal document. "
        "Below is the extracted text from the document:\n\n"
        f"{document_text}\n\n"
        f"User question: {user_input}"
    )

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": encrypt_text(user_input)
    })
    save_messages(st.session_state.user_id, st.session_state.messages)
    
    #st.write("Raw stored message:", st.session_state.messages[-1]["content"])


    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal information assistant. "
                "Provide general legal information in a neutral, educational manner. "
                "Do not give definitive legal advice, predictions, or guarantees. "
                "If the user asks for advice specific to their situation, clearly state "
                "that you are not a lawyer and recommend consulting a qualified legal professional. "
                "If jurisdiction is unclear, ask the user to specify their country."
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
        audio_out = speak_text(client, reply)
        st.audio(audio_out, format="audio/mp3")

    st.session_state.messages.append({
        "role": "assistant",
        "content": encrypt_text(reply)
    })
    save_messages(st.session_state.user_id, st.session_state.messages)
