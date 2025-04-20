# src/schemas/llm.py
from pydantic import BaseModel, Field
from typing import List

class SummarizationRequest(BaseModel):
    transcript: str = Field(..., description="The full transcript text to be summarized.")

class SummarizationResponse(BaseModel):
    summary: str = Field(..., description="The generated concise summary of the meeting.")
    action_items: List[str] = Field(default_factory=list, description="Action items extracted from the transcript.")
    llm_model_used: str = Field(..., description="The name of the LLM model used for summarization.")

class ChatRequest(BaseModel):
    transcript_context: str = Field(..., description="The transcript to provide context for the chat.")
    user_query: str = Field(..., description="The user's question about the transcript.")

class ChatResponse(BaseModel):
    ai_response: str = Field(..., description="The AI's answer to the user's query based on the transcript.")
    llm_model_used: str = Field(..., description="The name of the LLM model used for the chat response.")

