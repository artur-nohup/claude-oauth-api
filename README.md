# Claude OAuth API

A Docker-based API service that automates Claude.ai login and OAuth authorization flows using Playwright. This service maintains a persistent browser session to handle OAuth requests efficiently.

## 🚀 Features

- **Two-step login process** with email verification code support
- **Automated OAuth authorization** - clicks the authorize button and extracts the code
- **Persistent browser session** - login once, authorize multiple times
- **Visual mode with VNC** for bypassing anti-bot protection
- **Docker containerized** for easy deployment
- **API key authentication** for secure access
- **Ngrok integration** for public URL access
- **Health checks and status monitoring**
- **Interactive test client** included

## 📋 Prerequisites

- Docker and Docker Compose
- Claude.ai account with email access
- (Optional) Ngrok account for public URL access
- (Optional) VNC client for visual mode

## 🔧 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/artur-nohup/claude-oauth-api.git
cd claude-oauth-api

# Create environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your credentials:

```env
# API Authentication
API_KEY=your-secure-api-key-here

# Claude Login Email (password not needed - uses email verification)
CLAUDE_EMAIL=your-email@example.com

# Optional: Ngrok for public URL
NGROK_AUTHTOKEN=your-ngrok-auth-token

# Visual Mode (set to false for visual mode)
HEADLESS=true
```

### 3. Run in Headless Mode

```bash
# Start the services
docker-compose up --build

# Run in background
docker-compose up -d
```

### 4. Run in Visual Mode (Recommended)

Visual mode lets you see the browser and manually complete CAPTCHAs:

```bash
# Start visual mode
docker-compose -f docker-compose.visual.yml up --build

# Connect via VNC to localhost:5900 (no password)
# On Mac: open vnc://localhost:5900
```

The API will be available at:
- **Local**: `http://localhost:8000`
- **Ngrok** (if configured): Check `http://localhost:4040` for public URL

## 📚 API Documentation

### Health Check
```http
GET /
```

### Manual Login (Visual Mode)
```http
POST /login/manual
Headers:
  X-API-Key: your-api-key
```
Opens the login page in the browser for manual completion.

### Automated Login (Two-Step Process)

**Step 1: Request Verification Code**
```http
POST /login
Headers:
  X-API-Key: your-api-key
Body:
{
  "email": "your-email@example.com"
}
```

**Step 2: Complete Login with Code**
```http
POST /login
Headers:
  X-API-Key: your-api-key
Body:
{
  "email": "your-email@example.com",
  "verification_code": "123456"
}
```

### Process OAuth Authorization
```http
POST /oauth/authorize
Headers:
  X-API-Key: your-api-key
Body:
{
  "oauth_url": "https://claude.ai/oauth/authorize?client_id=..."
}
```

Response:
```json
{
  "success": true,
  "code": "authorization-code-here",
  "request_id": "uuid",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Check Session Status
```http
GET /status
Headers:
  X-API-Key: your-api-key
```

## 🧪 Testing

### Using the Interactive Test Client

```bash
# Test locally
python test_client.py

# Test with specific URL
python test_client.py https://your-url.com

# With environment variables
API_KEY=your-key API_BASE_URL=https://your-url python test_client.py
```

### Test Flow:
1. Choose option 1 to login to Claude (or use manual login in visual mode)
2. Enter your email and wait for verification code
3. Enter the 6-digit code from your email
4. Once logged in, choose option 3 to process OAuth URLs
5. Paste the OAuth URL when prompted
6. Receive the authorization code

## 🖥️ Visual Mode

Visual mode is the recommended approach as it bypasses Cloudflare protection:

1. **Start visual mode**: `docker-compose -f docker-compose.visual.yml up`
2. **Connect via VNC**: `localhost:5900` (no password)
3. **Call manual login**: `POST /login/manual`
4. **Complete login manually** in VNC viewer
5. **Process OAuth normally**

See [VISUAL_MODE.md](VISUAL_MODE.md) for detailed instructions.

## 🔒 Security Considerations

- **API Key**: Always use strong, randomly generated API keys
- **Environment**: Never commit `.env` files to version control
- **Container**: Runs as non-root user for enhanced security
- **Network**: Use HTTPS in production (ngrok provides this automatically)
- **Session**: Browser sessions persist until container restart

## 🐳 Docker Commands

```bash
# View logs
docker-compose logs -f claude-oauth-api

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Visual mode
docker-compose -f docker-compose.visual.yml up
```

## 🔍 Troubleshooting

### Login Issues
- Use visual mode for the first login
- Claude.ai may block automated browsers - use `/login/manual`
- Check email for verification codes (check spam folder)
- Codes expire quickly - enter them promptly

### VNC Issues
- Ensure port 5900 is available
- Try `127.0.0.1:5900` instead of `localhost:5900`
- Wait a few seconds after container start

### Container Issues
```bash
# Check logs
docker-compose logs claude-oauth-api

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

## 📝 Development

### Project Structure
```
claude-oauth-api/
├── main.py              # FastAPI application (headless)
├── main_visual.py       # FastAPI application (visual mode)
├── test_client.py       # Interactive test client
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Service orchestration (headless)
├── docker-compose.visual.yml  # Visual mode orchestration
├── start_visual.sh     # VNC startup script
├── VISUAL_MODE.md      # Visual mode documentation
├── .env.example        # Environment template
└── README.md          # This file
```

## 🎯 Use Cases

- **OAuth Testing**: Test OAuth flows in development
- **Integration Testing**: Automate Claude.ai authorization
- **Development Tools**: Build apps that integrate with Claude
- **CI/CD**: Automate OAuth authorization in pipelines

## 📄 License

This project is provided as-is for educational and development purposes. Please ensure you comply with Claude.ai's terms of service when using this tool.

## 🤝 Contributing

Feel free to open issues or submit pull requests to improve this project.

---

**⚠️ Important**: This tool automates browser interactions with Claude.ai. Always respect rate limits and terms of service.