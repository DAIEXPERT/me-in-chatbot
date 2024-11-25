import os
import shelve
from PyPDF2 import PdfReader
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

#st.title("Mounaim's resume")
#st.subheader("Interact with Mounaim's resume to learn more about his experience, skills, and achievements.")

import streamlit as st

# Assuming 'image_path' is the local file path or URL to the image you want to display
image_path = "pic.png"  # Replace with your image path

# Create two columns: one for the image and one for the title
col1, col2 = st.columns([1, 5])  # Adjust column width ratio (1:5 for image to title)

# Add image to the left column
with col1:
    st.image(image_path, width=50)  # Adjust width as needed

# Add title to the right column
with col2:
    st.title("Mounaim's Resume")
    st.subheader("Interact with Mounaim's resume to learn more about his experience, skills, and achievements.")


USER_AVATAR = "👤"
BOT_AVATAR = "🤖"
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# Ensure the OpenAI model is initialized in session state
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

# Function to load and process the PDF
def load_pdf_text(file_path):
    pdf_reader = PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

# Function to split text into chunks
def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=900,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Function to create a FAISS vectorstore from text chunks
def create_vectorstore(text_chunks):
    embeddings = HuggingFaceEmbeddings()
    vectorstore = FAISS.from_texts(text_chunks, embeddings)
    return vectorstore

# Function to load chat history from shelve
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])

# Function to save chat history to shelve
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# Load PDF and create vectorstore if not already loaded
if "vectorstore" not in st.session_state:
    pdf_text = load_pdf_text("CV_2024-11-23_Mounim_BELKHOUMALI.pdf")  # Ensure pdf.pdf exists in the same directory
    text_chunks = get_text_chunks(pdf_text)
    st.session_state.vectorstore = create_vectorstore(text_chunks)

# Function to retrieve context from the vectorstore
def retrieve_context(query):
    retriever = st.session_state.vectorstore.as_retriever()
    docs = retriever.get_relevant_documents(query)
    context = "\n".join([doc.page_content for doc in docs])
    return context

# Sidebar with a button to delete chat history
with st.sidebar:
    if st.button("Delete Chat History"):
        st.session_state.messages = []
        save_chat_history([])

# Display chat messages
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Main chat interface
if prompt := st.chat_input("Curious about Mounaim's skills or background? Ask me anything!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    # Retrieve context from vectorstore
    context = retrieve_context(prompt)

    # Combine user query with retrieved context
    full_prompt = f"Context: {context}\n\nQuestion: {prompt}"

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        full_response = ""
        for response in client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[{"role": "user", "content": full_prompt}],
            stream=True,
        ):
            full_response += response.choices[0].delta.content or ""
            message_placeholder.markdown(full_response + "|")
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Save chat history after each interaction
save_chat_history(st.session_state.messages)
