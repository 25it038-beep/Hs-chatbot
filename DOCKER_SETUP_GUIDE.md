## OPTION B: Add Chrome to Render via Docker

### What We're Doing
- Creating a custom Docker image with Chrome pre-installed
- Pushing it to Docker Hub
- Updating Render to use this custom image
- Browser automation will work on production!

---

## PREREQUISITES

You need a **Docker Hub account** (free):
1. Go to: https://hub.docker.com/
2. Sign up or log in
3. Note your username (e.g., `username`)

You also need **Docker Desktop** installed:
- Download: https://www.docker.com/products/docker-desktop
- Install and run it

---

## STEP 1: Build Docker Image Locally

Open **PowerShell** in the HSBot root directory:

```powershell
cd C:\Users\BS.Harshan seliyan\OneDrive\Documents\HSBot

# Replace YOUR_DOCKER_USERNAME with your actual Docker Hub username
docker build -t YOUR_DOCKER_USERNAME/hsbot-backend:latest -f backend/Dockerfile backend
```

**Example:**
```powershell
docker build -t harshan/hsbot-backend:latest -f backend/Dockerfile backend
```

This takes 5-10 minutes. Wait for "Successfully tagged..." message.

---

## STEP 2: Login to Docker Hub

```powershell
docker login
```

Enter your Docker Hub username and password when prompted.

---

## STEP 3: Push Image to Docker Hub

```powershell
# Replace YOUR_DOCKER_USERNAME
docker push YOUR_DOCKER_USERNAME/hsbot-backend:latest
```

This takes 2-5 minutes depending on internet speed.

When done, you'll see:
```
Digest: sha256:abc123...
Status: Downloaded newer image for YOUR_DOCKER_USERNAME/hsbot-backend:latest
```

---

## STEP 4: Update Render Service

1. Go to: https://dashboard.render.com/services
2. Click: **hs-chatbot-2** service
3. Click: **Settings** tab
4. Scroll down to: **Docker**
5. In **Docker Image** field, enter:
   ```
   YOUR_DOCKER_USERNAME/hsbot-backend:latest
   ```
   
   **Example:**
   ```
   harshan/hsbot-backend:latest
   ```

6. Click: **Save changes**
7. Render will auto-deploy (5-10 minutes)

---

## STEP 5: Verify Deployment

Once Render shows **"Live"** status (green dot):

1. Open desktop app: Press **Ctrl+Space**
2. Type: **"Open Google"**
3. **Chrome should open** and navigate to Google.com

---

## WHAT CHANGED

✅ **backend/Dockerfile** now includes:
- Chromium browser (lightweight)
- ChromeDriver
- Browser environment variables pre-set:
  - `BROWSER_ENABLED=1`
  - `BROWSER_HEADLESS=1`
  - `BROWSER_PERSISTENT_SESSION=1`

✅ **Docker Hub** has your custom image ready

✅ **Render** now uses your custom image instead of default Python

---

## TROUBLESHOOTING

### "Docker not installed"
- Download Docker Desktop: https://www.docker.com/products/docker-desktop
- Install and restart computer

### "docker build fails"
- Make sure you're in HSBot root directory
- Check backend/Dockerfile exists
- Try: `docker version` to verify Docker is running

### "docker push fails"
- Make sure you're logged in: `docker login`
- Check image exists: `docker images`

### "Render deploy is stuck"
- Go to Render logs: Click service → Logs tab
- Look for "Error" messages
- If you see Chrome errors, it means they're trying to start

---

## PERFORMANCE NOTES

On Render:
- First browser command: 10-15s (container startup + Chrome startup)
- Later commands: 3-5s
- Tab operations: <1s

---

## TIME ESTIMATE

| Step | Time |
|------|------|
| Build image | 5-10 min |
| Push to Docker Hub | 2-5 min |
| Update Render settings | 1 min |
| Render deploy | 5-10 min |
| **Total** | **15-30 min** |

---

## READY?

1. **Get Docker installed** (if not already)
2. **Create Docker Hub account** (if not already)
3. Run the 5 steps above
4. Come back and let me know when Render shows "Live" status!
