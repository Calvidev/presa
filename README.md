# La Presa · presa.calvi.dev

Booking site for the Calvi family summer home. Simple, minimalist, family-only.

---

## Stack

| Layer | Service |
|---|---|
| Frontend | Vanilla HTML/CSS/JS — `index.html` + `admin.html` |
| Hosting | GitHub Pages → `presa.calvi.dev` |
| Database | Google Sheets (never pauses, editable by anyone with access) |
| API | Google Apps Script Web App |
| Email | Resend → `presa@calvi.dev` |
| Email routing | Cloudflare Email Routing → forwards to `jccalvih@gmail.com` |
| DNS | Cloudflare (`calvi.dev`) |

---

## How it works

### Guest flow
1. Family member visits `presa.calvi.dev`
2. Clicks a start date then an end date on the calendar
3. Fills in name + email → confirms
4. Booking saved to Google Sheets via Apps Script — calendar updates for everyone
5. Apps Script fires two emails via Resend:
   - **Guest** → confirmation with check-in / check-out dates
   - **Owner** → notification at `presa@calvi.dev` (forwarded to Gmail)

### Admin flow
1. Owner visits `presa.calvi.dev/admin.html`
2. Logs in with the admin password
3. Can view, cancel (with cancellation email), or manually add bookings

---

## Repo structure

```
presa/
├── index.html          # Public booking page
├── admin.html          # Admin dashboard (password protected)
├── logo.jpg            # Circular logo (clipped via CSS)
├── CNAME               # presa.calvi.dev (GitHub Pages)
└── .gitignore
```

---

## Admin dashboard

**URL:** `presa.calvi.dev/admin.html`  
**Password:** `CalviPresa26`

| Feature | Description |
|---|---|
| Stats | Upcoming reservations, total nights booked, all-time total |
| Upcoming bookings | List with name, email, dates, nights — cancel button (sends email) |
| Manual booking | Add / block dates without a guest email confirmation |
| Past bookings | Collapsible history of all past stays |

---

## Google Sheets & Apps Script

**Sheet:** `1Cfk7dx0S05TF8NbCDxdl7ofk491hmhu5SkXKoRo0uVU`  
**Apps Script Web App:** `https://script.google.com/macros/s/AKfycbz_luah_ke0L_mOdzxuGvndcsE2wItACjK4FfF13SBuOzUJZcABNL1TsFl5lG9CDyLfGA/exec`

### Sheet columns (Sheet1)

| Column | Description |
|---|---|
| A — id | Timestamp-based unique ID |
| B — name | Guest full name |
| C — email | Guest email (or `—` for manual) |
| D — start_date | Check-in date (YYYY-MM-DD) |
| E — end_date | Check-out date (YYYY-MM-DD) |
| F — created_at | ISO timestamp |

### Apps Script endpoints

| Action | Method | Description |
|---|---|---|
| GET | — | Returns all bookings as JSON |
| POST `add` | Guest | Appends row, sends guest + owner emails |
| POST `manual` | Admin | Appends row, no emails (requires `secret`) |
| POST `delete` | Admin | Sends cancellation email, deletes row (requires `secret`) |

---

## Email (Resend)

- **Domain:** `calvi.dev` (verified)
- **From address:** `presa@calvi.dev`
- **Receiving:** Cloudflare Email Routing → `jccalvih@gmail.com`
- DNS records in Cloudflare: MX + DKIM TXT + SPF TXT on `send.calvi.dev`

---

## Deploy to production

```bash
cd ~/presa
git add index.html admin.html README.md
git commit -m "description"
git push
# GitHub Pages auto-deploys in ~60 seconds
```

---

## DNS (Cloudflare)

| Type | Name | Value | Notes |
|---|---|---|---|
| CNAME | `presa` | `calvidev.github.io` | **DNS only** (gray cloud) |
| MX | `calvi.dev` | Cloudflare mail servers | Email Routing (receiving) |
| MX | `send` | `feedback-smtp.us-east-1....` | Resend bounce handling |
| TXT | `resend._domainkey` | DKIM key | Resend sending auth |
| TXT | `send` | SPF record | Resend sending auth |
