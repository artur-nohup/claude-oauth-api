import os
import asyncio
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright, Browser
from dotenv import load_dotenv
import logging
from typing import Optional
from datetime import datetime
import uuid

load_dotenv()

app = FastAPI(title="Claude OAuth API", version="1.0.0")
API_KEY = os.getenv("API_KEY", "your-secret-api-key-here")
CLAUDE_EMAIL = os.getenv("CLAUDE_EMAIL", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class LoginRequest(BaseModel):
    email: str
    verification_code: Optional[str] = Field(None, description="6-digit verification code from email")

class OAuthRequest(BaseModel):
    oauth_url: str = Field(..., description="The OAuth authorization URL")

class OAuthResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    error: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class LoginResponse(BaseModel):
    status: str
    message: str
    session_active: bool = False

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

# Global browser instance for persistent session
browser_instance: Optional[Browser] = None
browser_context = None

@app.on_event("startup")
async def startup_event():
    """Initialize browser on startup"""
    global browser_instance, browser_context
    logger.info("Starting Claude OAuth API...")
    playwright = await async_playwright().start()
    browser_instance = await playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    browser_context = await browser_instance.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    logger.info("Browser initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser on shutdown"""
    global browser_instance
    if browser_instance:
        await browser_instance.close()
        logger.info("Browser closed")

@app.get("/")
async def root():
    return {"status": "healthy", "service": "Claude OAuth API", "version": "1.0.0"}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, api_key: str = Depends(verify_api_key)):
    """
    Login to Claude.ai - Two-step process:
    1. First call with email only
    2. Second call with email and verification code
    """
    global browser_context
    
    try:
        page = await browser_context.new_page()
        
        if not request.verification_code:
            # Step 1: Initial login with email
            logger.info(f"Starting login for {request.email}")
            await page.goto("https://claude.ai/login")
            await page.wait_for_load_state('networkidle')
            
            # Enter email
            await page.fill('input[type="email"]', request.email)
            await page.click('button:has-text("Continue with email")')
            
            # Wait for verification code screen
            try:
                await page.wait_for_selector('text=verification code', timeout=10000)
                await page.close()
                return LoginResponse(
                    status="verification_required",
                    message="Check your email for verification code",
                    session_active=False
                )
            except:
                await page.close()
                return LoginResponse(
                    status="error",
                    message="Failed to reach verification screen",
                    session_active=False
                )
        else:
            # Step 2: Complete login with verification code
            logger.info("Completing login with verification code")
            await page.goto("https://claude.ai/login")
            await page.wait_for_load_state('networkidle')
            
            # Enter email again
            await page.fill('input[type="email"]', request.email)
            await page.click('button:has-text("Continue with email")')
            
            # Wait for code input
            await page.wait_for_selector('input[inputmode="numeric"]', timeout=10000)
            
            # Enter verification code digit by digit
            code_inputs = await page.locator('input[inputmode="numeric"]').all()
            for i, digit in enumerate(str(request.verification_code)):
                if i < len(code_inputs):
                    await code_inputs[i].fill(digit)
            
            # Wait for login to complete
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # Check if logged in
            current_url = page.url
            if "claude.ai/chat" in current_url or "claude.ai/new" in current_url:
                # Keep the page open for OAuth flow
                logger.info("Login successful")
                return LoginResponse(
                    status="success",
                    message="Successfully logged in to Claude",
                    session_active=True
                )
            else:
                await page.close()
                return LoginResponse(
                    status="failed",
                    message="Login failed - please check credentials",
                    session_active=False
                )
                
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        if 'page' in locals():
            await page.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/oauth/authorize", response_model=OAuthResponse)
async def authorize_oauth(request: OAuthRequest, api_key: str = Depends(verify_api_key)):
    """
    Process OAuth authorization request
    Assumes user is already logged in via /login endpoint
    """
    global browser_context
    
    try:
        logger.info(f"Processing OAuth URL: {request.oauth_url}")
        
        # Use existing browser context
        page = None
        pages = browser_context.pages
        if pages:
            page = pages[0]  # Use existing page if available
        else:
            page = await browser_context.new_page()
        
        # Navigate to OAuth URL
        await page.goto(request.oauth_url)
        await page.wait_for_load_state('networkidle')
        
        # Check if we're on login page (session expired)
        if "login" in page.url:
            await page.close() if not pages else None
            raise HTTPException(
                status_code=401, 
                detail="Not logged in. Please use /login endpoint first."
            )
        
        # Look for authorize button
        logger.info("Looking for authorize button")
        
        # Try different possible selectors
        authorize_selectors = [
            'button:has-text("Authorize")',
            'button:has-text("Allow")',
            'button:has-text("Approve")',
            'button[type="submit"]:not(:disabled)',
            'button.btn-primary',
            'input[type="submit"][value*="Authorize"]'
        ]
        
        clicked = False
        for selector in authorize_selectors:
            try:
                element = page.locator(selector).first
                if await element.is_visible():
                    await element.click()
                    clicked = True
                    logger.info(f"Clicked authorize button: {selector}")
                    break
            except:
                continue
        
        if not clicked:
            # Log page content for debugging
            logger.error("Could not find authorize button")
            page_text = await page.text_content('body')
            logger.debug(f"Page content: {page_text[:500]}...")
            
            await page.close() if not pages else None
            return OAuthResponse(
                success=False,
                error="Could not find authorize button on page"
            )
        
        # Wait for redirect
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)
        
        # Extract code
        current_url = page.url
        logger.info(f"URL after authorization: {current_url}")
        
        # Try to extract code from URL
        if "code=" in current_url:
            code = current_url.split("code=")[1].split("&")[0]
            logger.info(f"Successfully extracted code from URL")
            
            # Don't close the page - keep session alive
            return OAuthResponse(
                success=True,
                code=code
            )
        
        # Try to extract from page content
        try:
            # Look for code in various formats
            code_selectors = [
                'code:has-text("")',
                'pre:has-text("")',
                '.authorization-code',
                'input[readonly]:not([type="password"])',
                'span.code',
                'div.code'
            ]
            
            for selector in code_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        code_text = await element.text_content()
                        if code_text and len(code_text) > 10:
                            logger.info("Found code in page content")
                            return OAuthResponse(
                                success=True,
                                code=code_text.strip()
                            )
                except:
                    continue
            
            # Check for specific text patterns
            page_content = await page.content()
            import re
            code_patterns = [
                r'code["\s:]+([A-Za-z0-9_-]{20,})',
                r'authorization.code["\s:]+([A-Za-z0-9_-]{20,})',
                r'>([A-Za-z0-9_-]{40,})<'
            ]
            
            for pattern in code_patterns:
                match = re.search(pattern, page_content)
                if match:
                    code = match.group(1)
                    logger.info("Found code via regex pattern")
                    return OAuthResponse(
                        success=True,
                        code=code
                    )
            
        except Exception as e:
            logger.error(f"Error extracting code: {e}")
        
        await page.close() if not pages else None
        return OAuthResponse(
            success=False,
            error="Could not extract authorization code from response"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth authorization failed: {str(e)}")
        if 'page' in locals() and page and not pages:
            await page.close()
        return OAuthResponse(
            success=False,
            error=str(e)
        )

@app.get("/status")
async def get_status(api_key: str = Depends(verify_api_key)):
    """Get current session status"""
    global browser_context
    
    try:
        pages = browser_context.pages if browser_context else []
        current_page = pages[0] if pages else None
        
        return {
            "browser_active": browser_context is not None,
            "pages_open": len(pages),
            "current_url": current_page.url if current_page else None,
            "logged_in": current_page and ("claude.ai/chat" in current_page.url or "claude.ai/new" in current_page.url) if current_page else False
        }
    except Exception as e:
        return {
            "browser_active": False,
            "pages_open": 0,
            "current_url": None,
            "logged_in": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
