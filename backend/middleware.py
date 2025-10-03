"""Middleware for correlation IDs, security headers, and structured logging."""

import uuid
from fastapi import Request, HTTPException
from fastapi.responses import Response
from .core.logging import log_json, Timer
from .core.config import settings
from .services.rate_limit import limiter

def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return str(uuid.uuid4())

# Security headers to apply to all responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY", 
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none';",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}

async def logging_middleware(request: Request, call_next):
    """Middleware for logging, correlation IDs, rate limiting, and security headers.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler
        
    Returns:
        Response with added headers and logging
    """
    # Generate correlation ID
    correlation_id = generate_correlation_id()
    request.state.correlation_id = correlation_id
    
    # Extract client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Rate limiting check
    if not limiter(client_ip, settings.RATE_CAPACITY, settings.RATE_REFILL_PER_SEC):
        log_json(
            "rate_limit_exceeded",
            ip=client_ip,
            path=request.url.path,
            cid=correlation_id
        )
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    # Log request start
    log_json(
        "request_start",
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params),
        ip=client_ip,
        user_agent=user_agent,
        cid=correlation_id
    )
    
    try:
        # Process request with timing
        with Timer() as timer:
            response: Response = await call_next(request)
        
        # Log successful request
        log_json(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(timer.dt * 1000, 2),
            ip=client_ip,
            cid=correlation_id
        )
        
        # Add correlation ID and security headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers.setdefault(header_name, header_value)
        
        return response
        
    except HTTPException as e:
        # Log HTTP exceptions (expected errors)
        log_json(
            "request_http_error", 
            method=request.method,
            path=request.url.path,
            status_code=e.status_code,
            error=e.detail,
            ip=client_ip,
            cid=correlation_id
        )
        raise
        
    except Exception as e:
        # Log unexpected errors
        log_json(
            "request_error",
            method=request.method, 
            path=request.url.path,
            error=str(e),
            error_type=type(e).__name__,
            ip=client_ip,
            cid=correlation_id
        )
        raise

async def security_middleware(request: Request, call_next):
    """Additional security middleware for request validation.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler
        
    Returns:
        Response after security checks
    """
    # Check for suspicious headers
    suspicious_headers = [
        "x-forwarded-host",
        "x-original-host", 
        "x-rewrite-url"
    ]
    
    for header in suspicious_headers:
        if header in request.headers:
            log_json(
                "suspicious_header_detected",
                header=header,
                value=request.headers[header],
                ip=request.client.host if request.client else "unknown"
            )
    
    # Validate content length for POST requests
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Request body too large ({content_length} bytes)"
            )
    
    response = await call_next(request)
    return response