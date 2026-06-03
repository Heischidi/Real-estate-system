from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter(tags=["Admin UI"])


@router.get("/admin", response_class=HTMLResponse)
async def get_admin_portal() -> HTMLResponse:
    """Serve the Admin Portal HTML page."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_file_path = os.path.join(
        current_dir, "..", "..", "static", "admin.html"
    )
    
    if not os.path.exists(static_file_path):
        return HTMLResponse(
            content="<html><body><h1>Admin Portal</h1><p>Dashboard HTML file not found.</p></body></html>",
            status_code=404,
        )
        
    with open(static_file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return HTMLResponse(content=content)
