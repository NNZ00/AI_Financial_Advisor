# Exposing the app publicly (tunnel + password)

This guide exposes the app **temporarily** on the internet through a *tunnel* (ngrok):
the app keeps running on your machine, but you get a public `https://…` link anyone
can open. Access is protected by a **shared password** (HTTP Basic Auth).

> ⚠️ Every analysis consumes your API keys (Google/Tavily) and takes ~2–3 minutes.
> Share the password **only** with people you trust. You can change it anytime.

---

## Prerequisites (one-time)

1. **Free ngrok account** → https://dashboard.ngrok.com/signup
2. From the dashboard, copy your **authtoken** (a personal secret string).
3. **Install ngrok** (pick one):
   - `winget install ngrok`  (recommended on Windows 10/11)
   - or download the zip from https://ngrok.com/download and unzip it.
4. Register the token (one-time):
   ```powershell
   ngrok config add-authtoken YOUR_TOKEN
   ```

---

## Every time you want to go live

### 1) Set the password
In your `.env` file (in the project root) set:
```
APP_USERNAME=advisor
APP_PASSWORD=a-strong-password-you-choose
```
(`.env` is gitignored, so the password never ends up in the code.)

### 2) Start the app (Terminal 1)
From the project root:
```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --port 8000
```
Leave this terminal open. (Locally, with the password set, check that opening
http://127.0.0.1:8000/ prompts you for username/password.)

### 3) Start the tunnel (Terminal 2)
Open a **second** terminal and run:
```powershell
ngrok http 8000
```
ngrok prints a line like:
```
Forwarding   https://a1b2-93-40-xx-xx.ngrok-free.app -> http://localhost:8000
```
That `https://…ngrok-free.app` address is **your public link**.

### 4) Share
Send whoever you want:
- **Link:** the `https://…ngrok-free.app` URL
- **Username:** `advisor`
- **Password:** the one you chose

On first open, ngrok (free plan) shows a "Visit Site" page — just click through.
Then the browser asks for username/password and the UI appears.

---

## To take it offline
- `Ctrl+C` in the **ngrok** terminal → the link stops working.
- `Ctrl+C` in the **uvicorn** terminal → stops the app.

## Things to know (free plan)
- Your **machine must stay on** with both terminals open; closing them takes the site offline.
- The **URL changes** each time you restart ngrok (a fixed URL needs a paid plan).
- The connection to the visitor is **HTTPS (encrypted)**.
- To **change the password**: edit `APP_PASSWORD` in `.env` and restart the app (Terminal 1).
- If you clear `APP_PASSWORD` (leave it empty), the app goes back to **no login** — don't do
  that while it's publicly exposed.

## Troubleshooting
- The browser doesn't ask for a password → make sure `APP_PASSWORD` in `.env` isn't empty and
  that you **restarted** uvicorn after changing it.
- "ERR_NGROK…" → make sure you ran `ngrok config add-authtoken …`.
- The proposal times out → on the free ngrok plan long requests work fine; other services
  (Cloudflare, some PaaS proxies) may cut requests off after ~100s.
