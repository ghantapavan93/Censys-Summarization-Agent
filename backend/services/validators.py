"""Validation module for request payload and security checks."""

from fastapi import HTTPException
from typing import Any, Dict, List

def assert_payload_size(body_bytes: int, max_bytes: int) -> None:
    """Validate payload size doesn't exceed limits.
    
    Args:
        body_bytes: Size of request body in bytes
        max_bytes: Maximum allowed bytes
        
    Raises:
        HTTPException: If payload too large
    """
    if body_bytes > max_bytes:
        raise HTTPException(
            status_code=413, 
            detail=f"Payload too large ({body_bytes:,} bytes > {max_bytes:,} bytes limit)"
        )

def assert_records_limit(record_count: int, max_records: int) -> None:
    """Validate number of records doesn't exceed limits.
    
    Args:
        record_count: Number of records in request
        max_records: Maximum allowed records
        
    Raises:
        HTTPException: If too many records
    """
    if record_count > max_records:
        raise HTTPException(
            status_code=422, 
            detail=f"Too many records ({record_count:,} > {max_records:,} limit)"
        )

def validate_record_structure(records: List[Dict[str, Any]]) -> None:
    """Validate basic record structure.
    
    Args:
        records: List of record dictionaries
        
    Raises:
        HTTPException: If record structure is invalid
    """
    if not isinstance(records, list):
        raise HTTPException(status_code=422, detail="Records must be a list")
    
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise HTTPException(
                status_code=422, 
                detail=f"Record {i} must be a dictionary"
            )
        
        # Ensure basic fields exist or can be defaulted
        if "id" not in record:
            record["id"] = f"record_{i}"
        
        if "text" not in record:
            record["text"] = ""

def validate_json_content(content: str) -> None:
    """Validate JSON content for basic security.
    
    Args:
        content: JSON content string
        
    Raises:
        HTTPException: If content appears malicious
    """
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="Empty JSON content")
    
    # Basic checks for potential attacks
    suspicious_patterns = [
        "__proto__",
        "constructor",
        "prototype",
        "eval(",
        "function(",
        "javascript:"
    ]
    
    content_lower = content.lower()
    for pattern in suspicious_patterns:
        if pattern in content_lower:
            raise HTTPException(
                status_code=422, 
                detail=f"Suspicious content detected: {pattern}"
            )