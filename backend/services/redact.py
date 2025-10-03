"""Privacy module for PII redaction and data sanitization."""

import re
from typing import Dict, List, Any

# Regex patterns for PII detection
IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_PATTERN = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")

def redact_text(text: str) -> str:
    """Redact PII from text content.
    
    Args:
        text: Input text to redact
        
    Returns:
        Text with PII patterns replaced with redaction markers
    """
    if not text or not isinstance(text, str):
        return text
    
    # Replace various PII patterns
    text = IPV4_PATTERN.sub("[REDACTED_IP]", text)
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", text)
    
    return text

def redact_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Redact PII from a list of record dictionaries.
    
    Args:
        records: List of record dictionaries
        
    Returns:
        List with PII redacted in text fields
    """
    redacted_records = []
    
    for record in records:
        redacted_record = dict(record)
        
        # Redact common text fields
        for field in ["text", "description", "content", "message", "notes"]:
            if field in redacted_record and isinstance(redacted_record[field], str):
                redacted_record[field] = redact_text(redacted_record[field])
        
        redacted_records.append(redacted_record)
    
    return redacted_records

def sanitize_user_input(data: str) -> str:
    """Sanitize user input for security.
    
    Args:
        data: Raw user input
        
    Returns:
        Sanitized input
    """
    if not data:
        return data
    
    # Basic XSS prevention
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        data = data.replace(char, '')
    
    return data.strip()