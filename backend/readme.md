# Running the AI Internship Agent with Chrome CDP

The AI Internship Agent uses **Playwright + Chrome DevTools Protocol (CDP)** to connect to an existing Chrome session.

This allows the agent to use an already authenticated browser session instead of opening a separate Chrome window and requiring the user to log in again.

## 1. Close Chrome

Close all currently running Chrome windows.

If Chrome is still running in the background:

1. Open **Task Manager**
2. Go to **Details**
3. Find `chrome.exe`
4. End all Chrome processes

## 2. Start Chrome with Remote Debugging

Open **Command Prompt (CMD)** and run:

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-debug"
```

If Chrome is installed in `Program Files (x86)`, use:

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-debug"
```

> **Note:** This starts Chrome using a separate `chrome-debug` profile. Log in to the required websites inside this Chrome profile.

Keep the CMD window open while using the agent.

## 3. Verify Chrome CDP

Open the following URL in the newly started Chrome:

```text
http://127.0.0.1:9222/json/version
```

If CDP is working, you should see JSON similar to:

```json
{
  "Browser": "Chrome/...",
  "webSocketDebuggerUrl": "ws://127.0.0.1:9222/..."
}
```

If the page cannot be reached, check that Chrome was started with:

```text
--remote-debugging-port=9222
```

You can also verify the port from CMD:

```cmd
netstat -ano | findstr :9222
```

A working setup should show port `9222` in a `LISTENING` state.

## 4. Start the FastAPI Backend

Open another terminal in the project directory:

```powershell
cd C:\path\to\ai-internship-agent
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

## 5. Open Swagger UI

Open:

```text
http://127.0.0.1:8000/docs
```

Find:

```text
POST /agent/apply
```

Click **Try it out**.

Enter the internship/application URL and profile ID:

```text
url = https://example.com/internship-application
profile_id = 2
```

Then click **Execute**.

## 6. Browser Connection

The browser implementation should connect using CDP:

```python
from playwright.async_api import async_playwright


class Browser:

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.connect_over_cdp(
            "http://127.0.0.1:9222"
        )

        if not self.browser.contexts:
            raise RuntimeError(
                "No Chrome browser context found"
            )

        self.context = self.browser.contexts[0]

        self.page = await self.context.new_page()

    async def open(self, url: str):

        await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await self.page.wait_for_timeout(2000)

    async def get_page_content(self):

        return await self.page.locator("body").inner_text()

    async def close(self):

        # Do NOT close the connected Chrome browser.
        self.page = None
        self.context = None
        self.browser = None

        if self.playwright:

            await self.playwright.stop()

            self.playwright = None
```

## 7. Important

When using:

```python
connect_over_cdp("http://127.0.0.1:9222")
```

Playwright connects to the existing Chrome instance.

Do **not** use:

```python
await self.browser.close()
```

because the browser belongs to the user's Chrome session.

Only stop the Playwright connection:

```python
await self.playwright.stop()
```

## Complete Startup Flow

```text
1. Close Chrome
        ↓
2. Start Chrome with --remote-debugging-port=9222
        ↓
3. Log in to required websites
        ↓
4. Verify http://127.0.0.1:9222/json/version
        ↓
5. Start FastAPI
        ↓
6. Open /docs
        ↓
7. POST /agent/apply
        ↓
8. Playwright connects to existing Chrome
        ↓
9. Open internship/application URL
        ↓
10. AI analyzes and fills the application
```

## Troubleshooting

### CDP URL does not open

Check:

```cmd
netstat -ano | findstr :9222
```

If nothing appears, Chrome was not started with remote debugging.

### Chrome opens but the website asks for login

Make sure you logged in using the **same Chrome profile started with**:

```text
--user-data-dir="%TEMP%\chrome-debug"
```

### Agent opens another Chrome window

Make sure your code does **not** contain:

```python
chromium.launch(...)
```

Instead, it should contain:

```python
chromium.connect_over_cdp(
    "http://127.0.0.1:9222"
)
```
