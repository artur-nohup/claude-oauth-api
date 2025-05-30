# Visual Mode Guide

This guide explains how to use the Claude OAuth API in visual mode, which allows you to see and interact with the browser to bypass anti-bot protections.

## Why Visual Mode?

Claude.ai uses Cloudflare protection that can detect and block automated browsers. Visual mode lets you:
- See the browser window via VNC
- Manually complete CAPTCHAs or challenges
- Debug login issues
- Intervene when automation is blocked

## Quick Start

### 1. Build and Run Visual Mode Container

```bash
# Build the visual Docker image
docker build -f Dockerfile.visual -t claude-oauth-visual .

# Run with docker-compose
docker-compose -f docker-compose.visual.yml up
```

### 2. Connect via VNC

The container exposes a VNC server on port 5900. Connect using any VNC client:

**On Mac:**
```bash
open vnc://localhost:5900
```

**On Windows:**
- Use RealVNC, TightVNC, or UltraVNC
- Connect to: `localhost:5900`
- No password required

**On Linux:**
```bash
vncviewer localhost:5900
```

### 3. Manual Login Process

1. Call the manual login endpoint:
```bash
curl -X POST http://localhost:8000/login/manual \
  -H "X-API-Key: test-api-key-123"
```

2. Look at your VNC viewer - you'll see the Claude login page
3. Manually complete the login process:
   - Enter email
   - Complete any CAPTCHA
   - Enter verification code
   - Wait for login to complete

4. Verify login status:
```bash
curl http://localhost:8000/status \
  -H "X-API-Key: test-api-key-123"
```

### 4. Process OAuth Requests

Once logged in, OAuth requests work normally:
```bash
curl -X POST http://localhost:8000/oauth/authorize \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "oauth_url": "https://claude.ai/oauth/authorize?..."
  }'
```

## Environment Variables

Set in your `.env` file:
```env
# Run in visual mode (false = headless)
HEADLESS=false

# Your API key
API_KEY=your-secure-key

# Email for automated login attempts
CLAUDE_EMAIL=your-email@example.com
```

## Tips

1. **First Login**: Always use manual login for the first time to ensure you can complete any challenges

2. **Session Persistence**: The browser session persists until the container restarts

3. **Multiple OAuth Requests**: Once logged in, you can process multiple OAuth requests without re-login

4. **Debugging**: Watch the VNC viewer to see exactly what's happening

5. **Performance**: Visual mode uses more resources than headless mode

## Troubleshooting

**Can't connect to VNC?**
- Ensure port 5900 is exposed: `docker ps`
- Check firewall settings
- Try `127.0.0.1:5900` instead of `localhost:5900`

**Black screen in VNC?**
- Wait a few seconds for Xvfb to start
- Restart the container
- Check logs: `docker logs claude-oauth-api-visual`

**Browser not appearing?**
- The browser only opens when you call `/login/manual` or `/oauth/authorize`
- Check the API logs for errors

**Login blocked by Cloudflare?**
- This is why we have visual mode! Complete the challenge manually
- Try moving the mouse naturally before clicking
- Wait a few seconds between actions

## Alternative: X11 Forwarding

If you prefer X11 forwarding instead of VNC:

```bash
# On Mac/Linux with X11
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e HEADLESS=false \
  -p 8000:8000 \
  claude-oauth-visual
```

## Security Note

Visual mode is intended for development and testing. In production:
- Use strong API keys
- Restrict VNC access
- Consider using a VNC password
- Run behind a secure network
