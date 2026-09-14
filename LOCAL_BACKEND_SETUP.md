## BROWSER AUTOMATION - LOCAL BACKEND SETUP

### Problem
- Render container doesn't have Chrome installed
- Browser commands timeout on Render
- Need to use LOCAL backend instead

### Solution: Start Backend Locally

#### Step 1: Start Backend (Terminal 1)
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Expected output:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000
```

#### Step 2: Build Desktop App with Local Backend (Terminal 2)
```powershell
cd frontend
npm run build

cd ../desktop
npm run tauri build
```

Wait for build to complete (~3 minutes).

#### Step 3: Run Desktop App
```powershell
cd desktop/src-tauri/target/release
./hsbot-desktop.exe
```

#### Step 4: Test Browser Command
1. Press Ctrl+Space
2. Type: "Open Google"
3. Watch Chrome open with Google.com loaded
4. Timing: 5-10 seconds (first time, Chrome startup)

---

### Configuration Changed
- `.env.local` now has: `VITE_API_URL=http://localhost:8000`
- Desktop app talks to LOCAL backend (http://localhost:8000)
- Instead of Render (https://hs-chatbot-2.onrender.com)

---

### Performance
| Operation | Speed |
|-----------|-------|
| Open Google | 5-10s (first time) |
| Search YouTube | 2-3s |
| Tab switch | <1s |
| Take screenshot | 1-2s |

---

### Troubleshooting

**Q: "Connection refused" error?**
- Make sure backend is running (Step 1)
- Check backend terminal for errors

**Q: "Chrome not found" error?**
- Chrome must be installed on your Windows machine
- It's already there (confirmed earlier)

**Q: "Opening..." but nothing happens?**
- Restart desktop app
- Make sure backend terminal shows no errors

---

### Notes
- Backend must stay running in Terminal 1
- You can close/open desktop app freely
- Changes to backend code auto-reload (--reload flag)

### To Switch Back to Render
1. Delete `VITE_API_URL=http://localhost:8000` from `frontend/.env.local`
2. Rebuild desktop: `cd desktop && npm run tauri build`
3. (But browser won't work unless Render gets Chrome)
