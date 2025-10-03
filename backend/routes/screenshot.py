from fastapi import APIRouter, Response, Query

router = APIRouter(tags=["screenshot"])


@router.get("/screenshot")
def screenshot(host: str = Query(...), port: int = Query(80)):
    # Placeholder: return a tiny blank 120x90 PNG without external dependencies.
    # In production, integrate a headless renderer and cache thumbnails.
    PNG_BLANK_120x90 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00x\x00\x00\x00Z\x08\x02\x00\x00\x00\x8a\xa9\x1c\x04"
        b"\x00\x00\x00\x0cIDATx\xda\x63\xf8\xff\xff?\x03\x03\x00\x06\x06\x01\x02\x89\x84\x8c\x1a"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(content=PNG_BLANK_120x90, media_type='image/png')
