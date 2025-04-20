# src/services/llm_service.py
import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser


from src.core.config import settings, logger
from src.schemas.llm import SummarizationResponse, ActionItemsResponse, ChatResponse

# Initialize Groq LLM
if not settings.GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found. Cannot initialize LLM Service.")
    llm = None
else:
    try:
        llm = ChatGroq(
            temperature=0.1,
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
            max_retries=2,
        )
        logger.info(f"ChatGroq LLM initialized with model: {settings.GROQ_MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize ChatGroq: {e}", exc_info=True)
        llm = None

# Prompt Templates
SUMMARY_ONLY_PROMPT_TEMPLATE = """System: You are an expert meeting assistant. Your task is to analyze the provided transcript and generate ONLY a concise summary of the main discussion points, key decisions, and overall outcome. Focus on clarity and accuracy.
\n---
Transcript Context:
{context}
---\n
Human: Based on the transcript provided, generate the concise summary.
Assistant:"""
summary_only_prompt = ChatPromptTemplate.from_template(SUMMARY_ONLY_PROMPT_TEMPLATE)

parser = PydanticOutputParser(pydantic_object=ActionItemsResponse)

action_items_prompt = PromptTemplate(
    template="""You are expert at identifying action items from transcripts. Analyze the provided transcript and extract specific, concrete tasks or actions mentioned in transcript.
    - Include the owner if mentioned (e.g., '- Send report - Alice').
    - If NO specific action items are identified, output the exact phrase: NO_ACTION_ITEMS
    \n---
    Transcript Context:
    {context}
    ---\n
    {format_instruction}
    Human: Based *only* on the transcript provided, list all specific action items using the specified format, or state NO_ACTION_ITEMS if none exist
    Assistant: """,
    input_variables=['context'],
    partial_variables={'format_instruction':parser.get_format_instructions()}
)

CHAT_PROMPT_TEMPLATE = """System: You are an AI assistant answering questions based *only* on the provided meeting transcript context. Be concise and directly address the user's query using information from the transcript. If the answer cannot be found in the transcript, explicitly state "The answer is not available in the provided transcript context." Do not make assumptions or use external knowledge.
\n---
Meeting Transcript Context:
{transcript_context}
---\n
Human: {user_query}
Assistant:"""
chat_prompt = ChatPromptTemplate.from_template(CHAT_PROMPT_TEMPLATE)


# Service Functions
async def generate_summary(transcript: str) -> SummarizationResponse:
    """Generates ONLY the summary from the transcript."""
    if not llm:
        raise ConnectionError("LLM service is not available.")
    if not transcript:
        raise ValueError("Transcript cannot be empty.")

    logger.info(f"Requesting summary from model {settings.GROQ_MODEL_NAME}")
    try:
        chain = summary_only_prompt | llm | StrOutputParser()
        summary_text = await chain.ainvoke({"context": transcript})
        logger.info("Summary LLM call successful.")

        return SummarizationResponse(summary=summary_text.strip())
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate summary: {e}")


async def extract_action_items(transcript: str) -> ActionItemsResponse:
    """Extracts ONLY the action items from the transcript."""
    if not llm:
        raise ConnectionError("LLM service is not available.")
    if not transcript:
        raise ValueError("Transcript cannot be empty.")

    logger.info(f"Requesting action items extraction from model {settings.GROQ_MODEL_NAME}")
    try:
        chain = action_items_prompt | llm | parser
        raw_output = await chain.ainvoke({"context": transcript})
        logger.info("Action items LLM call successful.")

        action_items_list = [item for item in raw_output.action_items if item] 
        return ActionItemsResponse(action_items=action_items_list)
    except Exception as e:
        logger.error(f"Action item extraction failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to extract action items: {e}")


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
        return ChatResponse(ai_response=result.strip())
    except Exception as e:
        logger.error(f"Chat query failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to get chat response: {e}")
