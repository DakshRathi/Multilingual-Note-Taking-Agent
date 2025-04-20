import streamlit as st
import requests
import time

# --- Configuration ---
FASTAPI_BASE_URL = "http://localhost:8000/api/v1"
TRANSCRIPTION_ENDPOINT = f"{FASTAPI_BASE_URL}/transcribe"
SUMMARIZATION_ENDPOINT = f"{FASTAPI_BASE_URL}/llm/summarize"
ACTION_ITEMS_ENDPOINT = f"{FASTAPI_BASE_URL}/llm/extract-action-items"
CHAT_ENDPOINT = f"{FASTAPI_BASE_URL}/llm/chat"

# --- Page Setup ---
st.set_page_config(
    page_title="Multilingual Meeting Notes Agent",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Styling (Optional) ---
st.markdown("""
<style>
    /* Center align the title */
    .stApp > header {
        background-color: transparent;
    }
    h1 {
        text-align: center;
        color: #2a7c90; /* Example custom color */
    }
    /* Style buttons */
    .stButton>button {
        border-radius: 20px;
        border: 1px solid #2a7c90;
        color: #2a7c90;
        background-color: #f0f2f6; /* Default Streamlit bg */
        transition: all 0.3s ease-in-out;
        margin-bottom: 10px; /* Add some space below buttons */
    }
    .stButton>button:hover {
        background-color: #2a7c90;
        color: white;
        border-color: #2a7c90;
    }
    /* Explicitly style disabled buttons */
    .stButton>button:disabled {
        background-color: #cccccc !important; /* Ensure override */
        border-color: #cccccc !important;
        color: #666666 !important;
        cursor: not-allowed !important;
    }
    .stFileUploader {
        border: 1px dashed #2a7c90;
        border-radius: 10px;
        padding: 1rem;
    }
    /* Styling for chat messages */
    .stChatMessage {
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }
    /* Style action items list */
    .action-items ul { list-style-type: disc; margin-left: 20px; }
    .action-items li { margin-bottom: 5px; }

</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
def init_session_state():
    defaults = {
        'transcript_data': None,
        'error_message': None,
        'is_loading': False,
        'uploaded_filename': None,
        'summary_data': None,
        'summarizing': False,
        'action_items_data': None,
        'summary_error': None,
        'chat_history': [],
        'chatting': False,
        'chat_error': None,
        'full_transcript_text': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# --- Helper Functions ---
def reset_state():
    keys_to_skip = ['audio_uploader', 'chat_input', 'transcribe_button', 'summarize_btn']  # widget keys to skip
    for k in st.session_state.keys():
        if k in keys_to_skip:
            continue
        if k == 'chat_history':
            st.session_state[k] = []
        elif k in ['is_loading', 'summarizing', 'chatting']:
            st.session_state[k] = False
        else:
            st.session_state[k] = None

# --- UI Layout ---
st.title("🎙️ Multilingual Meeting Notes Agent")
st.markdown("---")

col1, col2 = st.columns([0.25, 0.75], gap="medium")

with col1:
    st.header("Upload Audio File")

    uploaded_file = st.file_uploader(
        "Choose an audio file...",
        type=['mp3', 'wav', 'm4a', 'ogg', 'mp4', 'webm', 'mov', 'flac', 'mkv'],
        key="audio_uploader",
        on_change=reset_state,
        help="Upload your recording"
    )

    if uploaded_file:
        # Store filename for display
        if st.session_state.uploaded_filename != uploaded_file.name:
            st.session_state.uploaded_filename = uploaded_file.name
        st.info(f"File selected: `{st.session_state.uploaded_filename}`")

        # Transcription Button
        transcribe_disabled = st.session_state.is_loading or st.session_state.transcript_data is not None
        if st.button("✨ Transcribe Audio", key="transcribe_button", use_container_width=True, disabled=transcribe_disabled):
            reset_state()
            st.session_state.transcribe_clicked = True
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.is_loading = True
            with st.spinner("Transcribing audio... This might take a moment depending on the file size."):
                try:
                    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    resp = requests.post(TRANSCRIPTION_ENDPOINT, files=files)
                    resp.raise_for_status()
                    result = resp.json()
                    status = result.get("status")
                    if status == "TranscriptStatus.completed":
                        st.session_state.transcript_data = result
                        st.session_state.full_transcript_text = result.get('text', '')
                    else:
                        err = result.get('error', 'Unknown error')
                        st.session_state.error_message = f"Transcription failed: {err}"
                except Exception as e:
                    st.session_state.error_message = f"API Error: {e}"
                finally:
                    st.session_state.is_loading = False
                    st.rerun()

        # Summarization Button
        can_summarize = bool(st.session_state.full_transcript_text)
        sum_disabled = not can_summarize or st.session_state.summarizing
        if st.button("📝 Summarize Notes", key="summarize_btn", use_container_width=True, disabled=sum_disabled):
            st.session_state.summarizing = True
            with st.spinner("Generating summary and extracting action items..."):
                try:
                    payload = {"transcript": st.session_state.full_transcript_text}

                    # Call both endpoints
                    summary_resp = requests.post(SUMMARIZATION_ENDPOINT, json=payload, timeout=180)
                    summary_resp.raise_for_status()
                    summary_data = summary_resp.json()

                    action_resp = requests.post(ACTION_ITEMS_ENDPOINT, json=payload, timeout=180)
                    action_resp.raise_for_status()
                    action_items_data = action_resp.json()

                    # Merge action items into summary_data
                    summary_data["action_items"] = action_items_data.get("action_items", [])
                    st.session_state.summary_data = summary_data

                except Exception as e:
                    st.session_state.summary_error = f"Summarization/Action Items Error: {e}"
                finally:
                    st.session_state.summarizing = False
                    st.rerun()

    # Status Display
    st.markdown("---")
    st.subheader("Status")
    if st.session_state.is_loading:
        st.info("⏳ Transcription in progress...")
    elif st.session_state.summarizing:
        st.info("⏳ Summarization in progress...")
    elif st.session_state.chatting:
        st.info("⏳ Waiting for chat response...")
    elif st.session_state.error_message:
        st.error(st.session_state.error_message)
    elif st.session_state.summary_error:
        st.error(st.session_state.summary_error)
    elif st.session_state.transcript_data:
        st.success("✅ Ready")
    else:
        st.info("Upload a file to start.")

with col2:
    st.header("Output")

    if st.session_state.get("transcribe_clicked"):
        data = st.session_state.transcript_data
        st.subheader("Meeting Transcript (by Speaker)")
        utterances = data.get('utterances') or []
        if utterances:
            for utt in utterances:
                speaker = utt.get('speaker', 'Unknown')
                start_ms = utt.get('start', 0)
                timestamp = time.strftime('%M:%S', time.gmtime(start_ms/1000))
                with st.chat_message(speaker):
                    st.markdown(f"_{timestamp}_ | {utt.get('text','')}")
        else:
            st.text_area("Full Transcript", value=st.session_state.full_transcript_text, height=300, disabled=True)

        st.markdown("---")

        if st.session_state.summary_data:
            sd = st.session_state.summary_data
            st.subheader("Meeting Summary")
            st.markdown(sd.get('summary','_No summary generated._'))
            st.subheader("Action Items")
            items = sd.get('action_items', [])
            if items:
                for it in items:
                    st.markdown(f"- {it}")
            else:
                st.info("No specific action items identified.")
            st.caption(f"Model used: {sd.get('model_used','N/A')}")
            st.markdown("---")

        # Chat Interface
        st.subheader("Chat with Transcript Context")
        for msg in st.session_state.chat_history:
            role = msg['role']
            with st.chat_message(role):
                st.markdown(msg['content'])

        user_input = st.chat_input("Ask a question about the transcript...", disabled=st.session_state.chatting)
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chatting = True
            st.rerun()

        # On rerun, if chatting and last message is user, call Chat API
        if st.session_state.chatting and st.session_state.chat_history[-1]['role'] == 'user':
            with st.spinner("🤖 Thinking..."):
                try:
                    payload = {
                        "transcript_context": st.session_state.full_transcript_text,
                        "user_query": st.session_state.chat_history[-1]['content']
                    }
                    resp = requests.post(CHAT_ENDPOINT, json=payload, timeout=120)
                    resp.raise_for_status()
                    ai_resp = resp.json().get('ai_response','')
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_resp})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
                finally:
                    st.session_state.chatting = False
                    st.rerun()
    else:
        if not st.session_state.is_loading and not st.session_state.error_message:
            st.info("⬆️ Upload an audio file and click 'Transcribe Audio' to begin.")

# --- Footer ---
st.markdown("---")
st.caption("HOLON x KBI AI Agents Hackathon 2025 - Track 1 Submission")
