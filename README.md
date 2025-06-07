# Anti-Engagement-Farm Chrome Extension

A lightweight Manifest V3 Chrome extension that hides engagement-bait tweets (like “like & retweet,” “tag a friend,” “comment below”) on Twitter web and keeps a session log of what was removed.

---

## Features

- One-click toggle ON/OFF filtering
- Quick local regex filter for common bait patterns
- OpenAI-powered backend classification fallback
- Keeps an in-popup log of blocked tweets (author, snippet, time)
- “Clear Log” button in popup
- Persists toggle state and log in `chrome.storage.local`

---

## Installation (Load Unpacked)

1. Clone or download this repository.
2. Open Chrome and navigate to `chrome://extensions/`.
3. Enable **Developer mode** (top right).
4. Click **Load unpacked**, select the `anti-engagement-farm/` folder.
5. Ensure the extension appears in your toolbar.

---

## Usage

1. Click the extension icon in the Chrome toolbar.
2. Click **Turn ON** to start filtering engagement bait on Twitter.
3. Visit https://twitter.com/ — engagement-bait tweets will be hidden.
4. Open the popup again to view the **Blocked Tweets** log.
5. Click **Turn OFF** to disable filtering (log remains until you clear it).
6. Click **Clear Log** to erase the session’s history of hidden tweets.

---

## Configuration

By default, classification uses a backend proxy. To customize:

1. Edit `service_worker.js`.
2. Replace `BACKEND_URL` with your API endpoint, e.g.:

   ```js
   const BACKEND_URL = 'https://your-domain.com/api/classify';
   ```

3. Your backend should accept:
   ```json
   { "text": "full tweet text" }
   ```
   and return:
   ```json
   { "hide": true | false }
   ```

---

## Development

- **Content script**: `content.js`  
  Watches for new tweets, applies regex, sends uncertain cases to background.

- **Background**: `service_worker.js`  
  Caches classification results in memory, forwards to backend.

- **Popup**:  
  - Markup/CSS: `popup.html`, `popup.css`  
  - Logic: `popup.js`  

### Build & Test

No build step required—pure JS, HTML, CSS.  
To test changes:
1. Make edits in the `anti-engagement-farm/` directory.
2. Reload the extension at `chrome://extensions/`.

---

## Roadmap & Contributing

Planned improvements:

- Option to embed OpenAI key directly in the extension
- Better error handling and retry logic
- Configurable custom regex patterns
- UI enhancements (tweet preview, direct undo)
- Support for other social platforms
---
