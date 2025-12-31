import streamlit as st
from openai import OpenAI
import json
import os
import pdfplumber
import pytesseract
from PIL import Image

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

def extract_text_from_image(file):
    image = Image.open(file)
    return pytesseract.image_to_string(image).strip()




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
import uuid

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

document_text = ""

if uploaded_file is not None:
    st.info("Document uploaded successfully.")

    if uploaded_file.type == "application/pdf":
        document_text = extract_text_from_pdf(uploaded_file)
    else:
        document_text = extract_text_from_image(uploaded_file)


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a legal question or refer to the uploaded document...")

if uploaded_file is not None and user_input:
    user_input = (
        f"The user uploaded a document. "
        f"Please explain it in simple legal terms.\n\n"
        f"User question: {user_input}"
    )


if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_messages(st.session_state.user_id, st.session_state.messages)


    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                     "content": (  "You are a legal information assistant. "
"Provide general legal information in a neutral, educational manner. "
"Do not give definitive legal advice, predictions, or guarantees. "
"If the user asks for advice specific to their situation, clearly state "
"that you are not a lawyer and recommend consulting a qualified legal professional. "
"If jurisdiction is unclear, ask the user to specify their country."
                                )

                }
            ] + st.session_state.messages
        )
        reply = response.choices[0].message.content
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_messages(st.session_state.user_id, st.session_state.messages)

   

