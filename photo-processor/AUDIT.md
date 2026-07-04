# Stack Audit — Photo Processor PWA

Audit of the `Schierbeck2/Schierbeck2` repository (July 2026). The stack in
this repo is a Progressive Web App that receives shared Google Photos links
(via the Web Share Target API or manual paste) and forwards them to an n8n
webhook for processing.

## Critical issues (fixed in this branch)

### 1. Service worker had a syntax error — the whole app was broken
The service worker file began with the bare text line
`Service Worker for Share Target` (not a comment). A service worker that
fails to parse never installs, which means **the share target, offline
caching, and the PWA install prompt all silently did not work**. Fixed in
`sw.js`.

### 2. Files were misnamed and had no extensions
- "Photos Workflow" actually contained the PWA **manifest** → now `manifest.json`
- "Service worker For Share Target - n8n Workflow" contained **JavaScript**,
  not an n8n workflow → now `sw.js`
- "Web App HTML for Share target" → now `index.html`

The HTML registers `/sw.js` and links `/manifest.json`, so with the old names
nothing could be deployed without renaming by hand. Files now live under
`photo-processor/` with the names the code expects.

### 3. A missing icon would have blocked installation
`cache.addAll()` rejects the entire install if any single resource fails to
fetch. The cache list included `/images/icon-192.png` and
`/images/icon-512.png`, which don't exist in this repo — one 404 and the
service worker (and therefore the share target) never installs. Icons are now
cached best-effort; only `/`, `/index.html`, and `/manifest.json` are
required.

## Bugs fixed

- **Stale-forever cache**: the old cache-first strategy served `index.html`
  from cache indefinitely; any update required manually bumping `CACHE_NAME`.
  Navigations are now network-first with cache fallback for offline.
- **Dead webhook exclusion**: the fetch handler skipped URLs containing
  `webhook/google-photo-link`, but the real webhook path is
  `webhook-test/8cdbfb9b-…`. Replaced with a same-origin check that excludes
  all cross-origin requests.
- **False error on success**: `response.json()` threw if the n8n webhook
  replied with an empty or non-JSON body (the default for "Respond
  immediately"), so successful submissions showed an error. The response body
  is no longer parsed.
- **Repeat submission on reload**: after a share-target redirect, reloading
  the page re-submitted the same link to the webhook. The query string is now
  stripped with `history.replaceState` after processing.
- **No slow activation**: added `skipWaiting()` / `clients.claim()` so a new
  service worker takes effect immediately instead of after all tabs close.
- Two overlapping `fetch` listeners merged into one; URL matching now uses
  `URL.pathname` instead of string `includes`/`endsWith`.
- Manual input now rejects links that aren't Google Photos URLs
  (`photos.google.com` / `photos.app.goo.gl`) instead of posting anything to
  the webhook; input is `type="url"` and inline styles moved to CSS.
- Added `"scope": "/"` to the manifest.

## Remaining recommendations (need action outside this repo)

1. **Switch to the production webhook URL.** The app posts to
   `https://n8n.sputnik.sh/webhook-test/…`. n8n test webhooks only respond
   while the workflow is open and "listening" in the editor — in normal use
   every submission fails. Activate the workflow in n8n and change
   `WEBHOOK_URL` in `index.html` to the `/webhook/<id>` path.
2. **Add authentication to the webhook.** The webhook URL is public in this
   repository and accepts unauthenticated POSTs, so anyone can trigger (or
   flood) your workflow. Enable Header Auth on the n8n Webhook node and send
   the matching header from `processPhotoLink`, or at minimum rotate the
   webhook ID and keep it out of a public repo.
3. **Create the icons.** `images/icon-192.png` and `images/icon-512.png` are
   referenced by the manifest but don't exist. Chrome requires at least a
   192px icon for the PWA to be installable — and a share target only works
   from an *installed* PWA.
4. **Deploy from a proper location.** This is your GitHub **profile** repo
   (its README is your public profile). Consider moving `photo-processor/`
   to its own repository with static hosting (GitHub Pages, Netlify,
   Cloudflare Pages). Note the app uses absolute paths (`/sw.js`,
   `/manifest.json`, `/share-target`), so it must be served from a domain
   root, not a subpath like `username.github.io/repo/`.
5. **Commit the n8n workflow itself.** Despite the old file names, no actual
   n8n workflow JSON is in the repo, so the server-side half of the stack
   couldn't be audited or restored. Export the workflow from n8n
   (Download → JSON, with credentials stripped) and commit it alongside the
   app.
