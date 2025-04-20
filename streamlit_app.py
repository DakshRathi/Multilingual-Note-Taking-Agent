# streamlit_app.py
import streamlit as st
import requests
import time

# --- Configuration ---
FASTAPI_BACKEND_URL = "http://localhost:8000/api/v1/transcribe"

# --- Page Setup ---
st.set_page_config(
    page_title="Multilingual Meeting Notes Agent",
    page_icon="🎙️",
    layout="wide", 
    initial_sidebar_state="collapsed",
)

# --- Styling (Optional - Minor Enhancements) ---
# Inject custom CSS for subtle improvements if desired
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
    }
    .stButton>button:hover {
        background-color: #2a7c90;
        color: white;
        border-color: #2a7c90;
    }
    .stFileUploader {
        border: 1px dashed #2a7c90;
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
# Ensures variables persist across reruns
if 'transcript_data' not in st.session_state:
    st.session_state.transcript_data = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None

# --- Helper Functions ---
def reset_state():
    """Resets the session state variables for a new upload."""
    st.session_state.transcript_data = None
    st.session_state.error_message = None
    st.session_state.is_loading = False
    st.session_state.uploaded_filename = None

# --- UI Layout ---
st.title("🎙️ Multilingual Meeting Notes Agent")
st.markdown("---") 

col1, col2 = st.columns([0.25, 0.75], gap="medium")

with col1:
    st.header("Upload Meeting Audio")

    uploaded_file = st.file_uploader(
        "Choose an audio file...",
        type=['mp3', 'wav', 'm4a', 'ogg', 'mp4', 'webm', 'mov', 'flac', 'mkv'],
        key="audio_uploader",
        on_change=reset_state # Reset results when a new file is selected
    )

    if uploaded_file is not None:
        if st.session_state.uploaded_filename != uploaded_file.name:
            st.session_state.uploaded_filename = uploaded_file.name

        st.info(f"File selected: `{st.session_state.uploaded_filename}`")

        # Transcription Button
        if st.button("✨ Transcribe Audio", key="transcribe_button", use_container_width=True, disabled=st.session_state.is_loading):
            st.session_state.is_loading = True
            st.session_state.error_message = None 
            st.session_state.transcript_data = None

            # Show spinner while processing
            with st.spinner("Transcribing audio... This might take a moment depending on the file size."):
                try:
                    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    response = requests.post(FASTAPI_BACKEND_URL, files=files)
                    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                    result = response.json()

                    if result.get("status") == "TranscriptStatus.completed":
                        st.session_state.transcript_data = result
                        st.session_state.error_message = None
                    elif result.get("status") == "TranscriptStatus.error":
                        st.session_state.error_message = f"Transcription failed: {result.get('error', 'Unknown error')}"
                        st.session_state.transcript_data = None
                    else:
                        st.session_state.error_message = f"Unexpected response status: {result.get('status', 'N/A')}"
                        st.session_state.transcript_data = None

                except requests.exceptions.RequestException as e:
                    st.session_state.error_message = f"API Request Error: Could not connect to backend or timed out. ({e})"
                    st.session_state.transcript_data = None
                except Exception as e:
                    st.session_state.error_message = f"An unexpected error occurred: {e}"
                    st.session_state.transcript_data = None
                finally:
                    st.session_state.is_loading = False

with col2:
    st.header("Transcription Results")

    # Display loading indicator here as well if needed
    if st.session_state.is_loading:
        st.info("Processing... Please wait.")

    # Display Error Message if any
    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    # Display Transcription Data
    if st.session_state.transcript_data:
        data = st.session_state.transcript_data

        success_placeholder = st.empty()
        success_placeholder.success("Transcription Completed! 🎉")
        time.sleep(0.8)
        success_placeholder.empty()

        # -- Display Utterances with Speaker Labels (more detailed) --
        st.subheader("Meeting Transcript (by Speaker)")
        utterances = data.get('utterances')
        if utterances:
            # Use Streamlit Chat Message for a nice visual separation
            with st.container(height=300): # Make the transcript area scrollable
                for utt in utterances:
                    speaker_label = utt.get('speaker', 'Unknown')
                    avatar = "👤" if speaker_label == 'A' else "👥" if speaker_label else "❓" # Simple avatars
                    with st.chat_message(name=f"Speaker {speaker_label}", avatar=avatar):
                        start_ms = utt.get('start', 0)
                        # Format timestamp (optional)
                        # start_time_str = time.strftime('%M:%S', time.gmtime(start_ms // 1000))
                        # st.markdown(f"_{start_time_str}_") # Add timestamp if desired
                        st.write(utt.get('text', '')) # Use write for potentially longer text blocks
        else:
            # Fallback: Display full text if no utterances (or if preferred)
            st.subheader("Full Transcript")
            full_text = data.get('text', 'No text found.')
            st.text_area("Transcript:", value=full_text, height=250, disabled=True)

        st.markdown("---") # Separator

        # --- Placeholders for Future Features ---
        st.subheader("Next Steps")
        col_actions1, col_actions2, col_actions3 = st.columns(3)

        with col_actions1:
            # Placeholder for Summarization Button
            if st.button("Summarize Notes", key="summarize_btn", disabled=True, use_container_width=True):
                 st.info("Summarization feature coming soon!")
                 # In Phase 3: Call FastAPI /summarize endpoint

        with col_actions2:
            # Placeholder for Search
             st.text_input("Search Transcript...", key="search_input", disabled=True)
             # In Phase 4: Implement frontend search or call backend /search

        with col_actions3:
            # Placeholder for PDF Download
            if st.button("Download PDF", key="pdf_btn", disabled=True, use_container_width=True):
                 st.info("PDF export feature coming soon!")
                 # In Phase 4: Link to FastAPI /export/pdf endpoint

        # Placeholder for Chat Interface (might integrate differently later)
        st.text_input("Ask about the meeting...", key="chat_query_input", disabled=True)
        # In Phase 3: Implement chat logic calling /chat endpoint

    elif not st.session_state.is_loading and not st.session_state.error_message:
        st.info("Upload an audio file and click 'Transcribe Audio' to see the results.")

# --- Footer (Optional) ---
st.markdown("---")
st.caption("HOLON x KBI AI Agents Hackathon 2025 - Track 1 Submission")

