#streamlit run CHATBOT\frontend.py
import streamlit as st
from backend_tools import chatbot,retrieve_all_thread
from langchain_core.messages import HumanMessage
import uuid


#*********************************************** UTILITY FUNCTIONS**************************************************************#
# Function to generate unique thread ID
def generate_thread_id():
    thread_id  = str(uuid.uuid4())
    return thread_id

def reset_chat():
    thread_id  = generate_thread_id()
    st.session_state["thread_id"] =thread_id 
    add_thread(st.session_state["thread_id"])   
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_thread"]:
           st.session_state["chat_thread"].append(thread_id)

def load_conversation(thread_id):
    return chatbot.get_state(config = {"configurable": {"thread_id":thread_id}}).values["messages"]
 

#*********************************************** SESSION SETUP **************************************************************#
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_thread" not in st.session_state:
    st.session_state["chat_thread"] = retrieve_all_thread()
add_thread(st.session_state["thread_id"])

#*********************************************** SIDE BAR UI **************************************************************#

st.sidebar.title("Chatbot-ABHI$HEK")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("Cover$ation History")

for thread_id in st.session_state["chat_thread"]: 
 if st.sidebar.button(thread_id):
     st.session_state["thread_id"]= thread_id
     messages = load_conversation(thread_id)

     temp_messages = []
    
     for msg in messages:
        if isinstance(msg, HumanMessage):
            role='user'
        else:
            role='assistant'
        temp_messages.append({'role': role, 'content': msg.content})
        st.session_state['message_history'] = temp_messages   
   

#*********************************************** MAIN UI **************************************************************#

# CONFIG ={"configurable": {"thread_id": st.session_state["thread_id"]}}
CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

for message in st.session_state["message_history"]:
    with st.chat_message(message["role"]):
        st.text(message["content"])

user_input = st.chat_input("type here mamuji.....")

if user_input:

    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.text(user_input)
   
    with st.chat_message("assistant"):
        ai_message =st.write_stream( message_chunk.content for message_chunk,metadata in chatbot.stream({"messages": [HumanMessage(content=user_input)]},
        config=CONFIG,
        stream_mode="messages"))

    st.session_state["message_history"].append({"role": "assistant", "content": ai_message})