"""
InnerTube API - Main Application
A powerful, unlimited YouTube API wrapper

Created with ❤️ by Kobir Shah 🇧🇩 (Bangladesh)
"""
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx
from services.innertube_client import client_manager
import logging
from pathlib import Path

from config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    API_HOST,
    API_PORT,
    CORS_ORIGINS,
    CORS_METHODS,
    CORS_HEADERS
)

from routes import (
    youtube_router,
    channels_router,
    playlists_router,
    comments_router,
    music_router,
    advanced_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routers
app.include_router(youtube_router)
app.include_router(channels_router)
app.include_router(playlists_router)
app.include_router(comments_router)
app.include_router(music_router)
app.include_router(advanced_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the landing page"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    # Fallback HTML if static file doesn't exist
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>InnerTube API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            h1 { font-size: 3em; margin-bottom: 10px; }
            a {
                color: #fff;
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
                margin: 10px 5px;
            }
            a:hover { background: rgba(255,255,255,0.3); }
        </style>
    </head>
    <body>
        <h1>🚀 InnerTube API</h1>
        <p>Your powerful, unlimited YouTube API wrapper is running!</p>
        <div>
            <a href="/docs">📚 API Documentation</a>
            <a href="/redoc">📖 ReDoc</a>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": API_VERSION,
        "service": "InnerTube API"
    }

@app.get("/api/stream/{video_id}")
async def stream_video(video_id: str, request: Request):
    player_data = client_manager.player(video_id=video_id, client_type="ANDROID")
    
    formats = player_data.get("streamingData", {}).get("formats", [])
    stream_url = None
    
    for fmt in formats:
        if fmt.get("url"):
            stream_url = fmt["url"]
            if str(fmt.get("itag")) == "18":
                break

    if not stream_url:
        raise HTTPException(status_code=404, detail="Stream MP4 nao encontrado")

    headers = {
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip"
    }
    if "range" in request.headers:
        headers["Range"] = request.headers["range"]

    client = httpx.AsyncClient(follow_redirects=True)
    req = client.build_request("GET", stream_url, headers=headers)
    r = await client.send(req, stream=True)

    response_headers = {
        "Content-Type": r.headers.get("Content-Type", "video/mp4"),
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
    }
    if "Content-Length" in r.headers:
        response_headers["Content-Length"] = r.headers["Content-Length"]
    if "Content-Range" in r.headers:
        response_headers["Content-Range"] = r.headers["Content-Range"]

    async def iter_stream():
        try:
            async for chunk in r.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    return StreamingResponse(
        iter_stream(),
        status_code=r.status_code,
        headers=response_headers,
        media_type="video/mp4"
    )


@app.get("/info")
async def api_info():
    """Get API information"""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": "Powerful YouTube API wrapper with unlimited features",
        "endpoints": {
            "youtube": [
                "/api/search",
                "/api/video/{video_id}",
                "/api/player/{video_id}",
                "/api/next/{video_id}",
                "/api/browse/{browse_id}",
                "/api/trending",
                "/api/homepage"
            ],
            "channels": [
                "/api/channel/{channel_id}",
                "/api/channel/{channel_id}/videos",
                "/api/channel/{channel_id}/playlists",
                "/api/channel/{channel_id}/about",
                "/api/channel/{channel_id}/community"
            ],
            "playlists": [
                "/api/playlist/{playlist_id}",
                "/api/playlist/{playlist_id}/videos"
            ],
            "comments": [
                "/api/comments/{video_id}"
            ],
            "music": [
                "/api/music/search",
                "/api/music/home",
                "/api/music/artist/{artist_id}",
                "/api/music/album/{album_id}",
                "/api/music/playlist/{playlist_id}"
            ],
            "advanced": [
                "/api/batch",
                "/api/captions/{video_id}",
                "/api/livestream/{video_id}",
                "/api/shorts/{shorts_id}",
                "/api/analytics",
                "/api/cache/clear"
            ]
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info(f"Server running at http://{API_HOST}:{API_PORT}")
    logger.info(f"Documentation available at http://{API_HOST}:{API_PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )
