import streamlit as st
from openai import OpenAI
import json
import os
import pdfplumber
import base64
import uuid

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

def transcribe_audio(client, audio_file):
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

st.set_page_config(page_title="Legal AI Chatbot", page_icon="⚖️")

st.markdown("""
⚠️ **Disclaimer**  
This chatbot provides general legal information only.  
It is not a lawyer and does not provide legal advice.  
Always consult a qualified legal professional.
""")

st.markdown("### Login")
st.info("Google Sign-In will be enabled shortly.")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

query_params = st.experimental_get_query_params()

if "user_id" in query_params:
    st.session_state.user_id = query_params["user_id"][0]
else:
    new_id = str(uuid.uuid4())
    st.session_state.user_id = new_id
    st.experimental_set_query_params(user_id=new_id)

if "messages" not in st.session_state:
    st.session_state.messages = load_messages(st.session_state.user_id)

st.markdown("## ⚖️ Legal Assistant")

uploaded_file = st.file_uploader(
    "Upload a legal document (image or PDF)",
    type=["png", "jpg", "jpeg", "pdf"]
)

audio_file = st.file_uploader(
    "Upload an audio question (WAV or MP3)",
    type=["wav", "mp3"]
)

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
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a legal question or refer to the uploaded document...")

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
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_messages(st.session_state.user_id, st.session_state.messages)

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

    if image_bytes:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_input},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode()}"
                    }
                }
            ]
        })
    else:
        messages.extend(st.session_state.messages)

    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        st.markdown(reply)
        audio_out = speak_text(client, reply)
        st.audio(audio_out, format="audio/mp3")

    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_messages(st.session_state.user_id, st.session_state.messages)



