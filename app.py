import streamlit as st
from openai import OpenAI

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

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())


if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("## ⚖️ Legal Assistant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a legal question...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal information assistant. You must not provide definitive legal advice. Always remind users to consult a lawyer."
                }
            ] + st.session_state.messages
        )
        reply = response.choices[0].message.content
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
