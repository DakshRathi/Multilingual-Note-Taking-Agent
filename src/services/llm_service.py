# src/services/llm_service.py
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain

from src.core.config import settings, logger
from src.schemas.llm import SummarizationResponse, ChatResponse

# --- Initialize Groq LLM ---
if not settings.GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found. Cannot initialize LLM Service.")
    llm = None
else:
    try:
        llm = ChatGroq(
            temperature=0.1, # Low temperature for factual summary/chat
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
            max_retries=2,
        )
        logger.info(f"ChatGroq LLM initialized with model: {settings.GROQ_MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize ChatGroq: {e}", exc_info=True)
        llm = None

# --- Prompt Templates ---

# Summarization Prompt (instructs structure for easier parsing)
SUMMARY_PROMPT_TEMPLATE = """System: You are an expert meeting assistant specialized in summarizing multilingual transcripts. Your task is to analyze the provided transcript and generate:
1.  **Concise Summary:** A brief overview of the main discussion points, key decisions, and overall outcome. Focus on clarity and accuracy.
2.  **Action Items:** A numbered list of specific tasks or actions assigned during the meeting. If an owner is mentioned, include them. If no action items are identified, state "No specific action items were identified."

Use the following structure for your response:

**Summary:**
[Your concise summary here]

**Action Items:**
1. [Action item 1] - [Owner if mentioned, otherwise omit]
2. [Action item 2] - [Owner if mentioned, otherwise omit]
...
(or "No specific action items were identified.")

---
Transcript Context:
{context}
---

Human: Based on the transcript provided, generate the summary and action items following the specified structure.
Assistant:"""
summary_prompt = ChatPromptTemplate.from_template(SUMMARY_PROMPT_TEMPLATE)

# Chat Prompt (focused Q&A based *only* on context)
CHAT_PROMPT_TEMPLATE = """System: You are an AI assistant answering questions based *only* on the provided meeting transcript context. Be concise and directly address the user's query using information from the transcript. If the answer cannot be found in the transcript, explicitly state "The answer is not available in the provided transcript context." Do not make assumptions or use external knowledge.

---
Meeting Transcript Context:
{transcript_context}
---

Human: {user_query}
Assistant:"""
chat_prompt = ChatPromptTemplate.from_template(CHAT_PROMPT_TEMPLATE)


# --- Service Functions ---
def _parse_summary_and_actions(llm_output: str) -> tuple[str, list[str]]:
    """Parses the LLM output structured by the prompt into summary and actions."""
    summary = "Summary could not be extracted."
    action_items = []

    summary_match = re.search(r"\*\*Summary:\*\*(.*?)\*\*Action Items:\*\*", llm_output, re.DOTALL | re.IGNORECASE)
    if summary_match:
        summary = summary_match.group(1).strip()

    actions_match = re.search(r"\*\*Action Items:\*\*(.*)", llm_output, re.DOTALL | re.IGNORECASE)
    if actions_match:
        action_section = actions_match.group(1).strip()
        if "no specific action items" not in action_section.lower():
            # Split by newline and filter out empty lines, then remove numbering
            potential_items = [line.strip() for line in action_section.splitlines() if line.strip()]
            # Basic cleaning: remove initial numbering like "1.", "2." etc.
            action_items = [re.sub(r"^\d+\.\s*", "", item) for item in potential_items]
        # If the explicit "no items" phrase is there, action_items remains empty []

    # Fallback if structure isn't perfect but keywords are present
    if summary == "Summary could not be extracted." and "**Summary:**" in llm_output:
        summary = llm_output.split("**Summary:**")[1].split("**Action Items:**")[0].strip() # Less robust

    return summary, action_items


async def summarize_transcript(transcript: str) -> SummarizationResponse:
    """Generates summary and extracts action items from the transcript."""
    if not llm:
        raise ConnectionError("LLM service is not available (Initialization failed or API key missing).")
    if not transcript:
        raise ValueError("Transcript cannot be empty.")

    logger.info(f"Requesting summarization from model {settings.GROQ_MODEL_NAME}")
    try:
        # Using create_stuff_documents_chain for single-call summarization
        # Wrap the transcript in a Document object as expected by the chain
        documents = [Document(page_content=transcript)]
        chain = create_stuff_documents_chain(llm, summary_prompt)

        # Invoke the chain
        result = await chain.ainvoke({"context": documents})
        logger.info("Summarization LLM call successful.")

        # Parse the structured output
        summary_text, action_items_list = _parse_summary_and_actions(result)

        return SummarizationResponse(
            summary=summary_text,
            action_items=action_items_list,
            llm_model_used=settings.GROQ_MODEL_NAME
        )

    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        # Re-raise a more specific error or handle it
        raise RuntimeError(f"Failed to generate summary: {e}")


async def answer_query(transcript_context: str, user_query: str) -> ChatResponse:
    """Answers a user query based on the provided transcript context."""
    if not llm:
        raise ConnectionError("LLM service is not available.")
    if not transcript_context or not user_query:
        raise ValueError("Transcript context and user query cannot be empty.")

    logger.info(f"Requesting chat response from model {settings.GROQ_MODEL_NAME}")
    try:
        chain = chat_prompt | llm | StrOutputParser()

        result = await chain.ainvoke({
            "transcript_context": transcript_context,
            "user_query": user_query
        })
        logger.info("Chat LLM call successful.")

        return ChatResponse(
            ai_response=result.strip(),
            llm_model_used=settings.GROQ_MODEL_NAME
        )
    except Exception as e:
        logger.error(f"Chat query failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get chat response: {e}")
