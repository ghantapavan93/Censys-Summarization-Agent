"""Agent state management for data processing workflow."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """State object for the agent processing workflow."""
    
    # Input data
    data: Dict[str, Any] = Field(default_factory=dict, description="Input data containing records")
    
    # Processing results
    insights: Optional[Dict[str, Any]] = Field(default=None, description="Generated insights from data analysis")
    summary: Optional[Dict[str, Any]] = Field(default=None, description="AI-generated summary")
    
    # Processing metadata
    record_count: int = Field(default=0, description="Number of records processed")
    processing_time: Optional[float] = Field(default=None, description="Total processing time in seconds")
    used_map_reduce: bool = Field(default=False, description="Whether map-reduce was used for large datasets")
    
    # Error handling
    errors: List[str] = Field(default_factory=list, description="List of processing errors")
    warnings: List[str] = Field(default_factory=list, description="List of processing warnings")
    # Retrieval/RAG info (optional)
    retrieval: Optional[Dict[str, Any]] = Field(default=None, description="RAG query and top-k hits")
    # Toggle for optional LLM polishing (defaults to deterministic only)
    use_llm: bool = Field(default=False, description="If true, polish deterministic overview with Ollama")
    
class Config:
    """Pydantic configuration."""
    arbitrary_types_allowed = True