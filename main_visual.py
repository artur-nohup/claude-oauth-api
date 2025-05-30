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
import random

load_dotenv()

app = FastAPI(title="Claude OAuth API", version="1.0.0")
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")
CLAUDE_EMAIL = os.getenv("CLAUDE_EMAIL", "")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Request/Response models
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

# Global browser instance
browser_instance: Optional[Browser] = None
browser_context = None

async def create_stealth_browser():
    """Create a browser instance with stealth settings"""
    playwright = await async_playwright().start()
    
    # Randomize viewport slightly
    viewport_width = 1920 + random.randint(-100, 100)
    viewport_height = 1080 + random.randint(-100, 100)
    
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            f'--window-size={viewport_width},{viewport_height}',
        ],
        # Remove indicators of headless mode
        chromium_sandbox=False,
    )
    
    context = await browser.new_context(
        viewport={'width': viewport_width, 'height': viewport_height},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['geolocation'],
        geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
        color_scheme='light',
        device_scale_factor=1,
        has_touch=False,
        java_script_enabled=True,
        bypass_csp=False,
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
    )
    
    # Add stealth scripts to avoid detection
    await context.add_init_script("""
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override chrome
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        
        // Override console.debug to prevent detection
        const originalConsoleDebug = console.debug;
        console.debug = function(...args) {
            if (args[0] && args[0].includes('HeadlessChrome')) return;
            return originalConsoleDebug.apply(console, args);
        };
    """)
    
    return browser, context

@app.on_event("startup")
async def startup_event():
    """Initialize browser on startup"""
    global browser_instance, browser_context
    logger.info(f"Starting Claude OAuth API (Headless: {HEADLESS})...")
    
    try:
        browser_instance, browser_context = await create_stealth_browser()
        logger.info("Stealth browser initialized successfully")
        
        if not HEADLESS:
            logger.info("Running in VISUAL mode - browser window is visible")
            logger.info("You can interact with the browser if needed")
    except Exception as e:
        logger.error(f"Failed to initialize browser: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up browser on shutdown"""
    global browser_instance
    if browser_instance:
        await browser_instance.close()
        logger.info("Browser closed")

@app.get("/")
async def root():
    return {
        "status": "healthy", 
        "service": "Claude OAuth API", 
        "version": "1.0.0",
        "mode": "headless" if HEADLESS else "visual"
    }

@app.post("/login/manual")
async def manual_login(api_key: str = Depends(verify_api_key)):
    """
    Open Claude login page for manual login
    Use this when automated login is blocked
    """
    global browser_context
    
    try:
        page = await browser_context.new_page()
        
        # Add random delay to seem more human
        await asyncio.sleep(random.uniform(1, 3))
        
        logger.info("Opening Claude login page for manual login...")
        await page.goto("https://claude.ai/login")
        
        return {
            "status": "opened",
            "message": "Login page opened. Please complete login manually.",
            "instructions": [
                "1. Look at the browser window (or connect via VNC on port 5900)",
                "2. Complete the login process manually",
                "3. Once logged in, use the /status endpoint to verify",
                "4. Then you can use /oauth/authorize for OAuth flows"
            ]
        }
    except Exception as e:
        logger.error(f"Error opening login page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, api_key: str = Depends(verify_api_key)):
    """
    Automated login with email verification
    May fail if Cloudflare protection is active
    """
    global browser_context
    
    try:
        page = await browser_context.new_page()
        
        # Add random delays to seem more human
        await asyncio.sleep(random.uniform(1, 2))
        
        # Random mouse movements
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        
        if not request.verification_code:
            # Step 1: Initial login with email
            logger.info(f"Starting login for {request.email}")
            await page.goto("https://claude.ai/login")
            
            # Wait a bit before interacting
            await asyncio.sleep(random.uniform(2, 4))
            
            # Type email like a human
            email_input = await page.wait_for_selector('input[type="email"]', timeout=10000)
            await email_input.click()
            await asyncio.sleep(random.uniform(0.5, 1))
            
            # Type slowly
            for char in request.email:
                await email_input.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Find and click continue button
            await asyncio.sleep(random.uniform(1, 2))
            continue_button = await page.wait_for_selector('button:has-text("Continue with email")')
            await continue_button.click()
            
            # Check if we hit a challenge
            await asyncio.sleep(3)
            if "challenge" in page.url or await page.locator('iframe[title*="challenge"]').is_visible():
                await page.close()
                return LoginResponse(
                    status="challenge_detected",
                    message="Cloudflare challenge detected. Please use /login/manual for manual login.",
                    session_active=False
                )
            
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
                    message="Failed to reach verification screen - may be blocked",
                    session_active=False
                )
        else:
            # Step 2: Complete login with verification code
            logger.info("Completing login with verification code")
            # Implementation similar to above but with code entry
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        if 'page' in locals():
            await page.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/oauth/authorize", response_model=OAuthResponse)
async def authorize_oauth(request: OAuthRequest, api_key: str = Depends(verify_api_key)):
    """Process OAuth authorization request"""
    global browser_context
    
    try:
        pages = browser_context.pages
        page = pages[0] if pages else await browser_context.new_page()
        
        # Add human-like behavior
        await asyncio.sleep(random.uniform(1, 2))
        
        logger.info(f"Processing OAuth URL: {request.oauth_url}")
        await page.goto(request.oauth_url)
        
        # Wait and check for authorize button
        await asyncio.sleep(random.uniform(2, 4))
        
        # Implementation continues...
        
    except Exception as e:
        logger.error(f"OAuth authorization failed: {str(e)}")
        return OAuthResponse(success=False, error=str(e))

@app.get("/status")
async def get_status(api_key: str = Depends(verify_api_key)):
    """Get current session status"""
    global browser_context
    
    try:
        pages = browser_context.pages if browser_context else []
        current_page = pages[0] if pages else None
        
        logged_in = False
        if current_page:
            current_url = current_page.url
            logged_in = "claude.ai/chat" in current_url or "claude.ai/new" in current_url
        
        return {
            "browser_active": browser_context is not None,
            "pages_open": len(pages),
            "current_url": current_page.url if current_page else None,
            "logged_in": logged_in,
            "mode": "headless" if HEADLESS else "visual"
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
    # Check if running in Docker
    in_docker = os.path.exists('/.dockerenv')
    host = "0.0.0.0" if in_docker else "127.0.0.1"
    uvicorn.run(app, host=host, port=8000)
