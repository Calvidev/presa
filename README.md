# La Presa · presa.calvi.dev

Booking site for the Calvi family summer home. Simple, minimalist, family-only.

---

## Stack

| Layer | Service |
|---|---|
| Frontend | Vanilla HTML/CSS/JS — single `index.html` |
| Hosting | GitHub Pages → `presa.calvi.dev` |
| Database | Supabase (Postgres) |
| Email | Resend → `presa@calvi.dev` |
| DNS | Cloudflare (`calvi.dev`) |

---

## How it works

1. Family member visits `presa.calvi.dev`
2. Clicks a start date then an end date on the calendar
3. Fills in name + email → confirms
4. Booking is saved to Supabase — calendar updates for everyone instantly
5. Resend fires two emails:
   - **Guest** → confirmation with dates
   - **Owner** → notification at `presa@calvi.dev`

---

## Repo structure

```
presa/
├── index.html                        # Public booking page
├── admin.html                        # Admin dashboard (login required)
├── logo.jpg                          # Circular logo (clipped via CSS)
├── CNAME                             # presa.calvi.dev (GitHub Pages)
├── supabase/
│   └── functions/
│       └── send-confirmation/
│           └── index.ts              # Edge Function — sends emails via Resend
└── .gitignore
```

## Admin dashboard

URL: `presa.calvi.dev/admin`

Login: `jccalvih@gmail.com` via Supabase Auth

Features:
- View all upcoming and past bookings
- Cancel / delete a booking (frees up those dates instantly)
- Add manual bookings (block dates for family use)
- Stats: upcoming reservations, total nights booked, total bookings

---

## Supabase

**Project:** `xlkvhrqlmimzvtfasktd.supabase.co`

### Table: `bookings`

| Column | Type | Notes |
|---|---|---|
| `id` | bigint | Auto-generated PK |
| `name` | text | Guest full name |
| `email` | text | Guest email |
| `start_date` | date | Check-in |
| `end_date` | date | Check-out |
| `created_at` | timestamptz | Auto |

### RLS Policies
- `SELECT` → public (calendar shows booked dates to everyone)
- `INSERT` → public (anyone can book)

### Edge Function: `send-confirmation`
- Triggered by a **Database Webhook** on `bookings INSERT`
- Sends confirmation email to guest
- Sends notification email to `presa@calvi.dev`
- Secret: `RESEND_API_KEY` stored in Supabase secrets

---

## Email (Resend)

- **Domain:** `calvi.dev` (verified)
- **From address:** `presa@calvi.dev`
- DNS records added in Cloudflare (MX + DKIM TXT + SPF TXT on `send.calvi.dev`)

---

## Local development

```bash
# Serve locally
cd ~/presa
python3 -m http.server 8743
# → http://localhost:8743

# Deploy Edge Function
supabase functions deploy send-confirmation --no-verify-jwt

# Update secrets
supabase secrets set RESEND_API_KEY=re_...
```

## Deploy to production

```bash
cd ~/presa
git add index.html          # or whatever changed
git commit -m "description"
git push
# GitHub Pages auto-deploys in ~60 seconds
```

---

## DNS (Cloudflare)

| Type | Name | Value |
|---|---|---|
| CNAME | `presa` | `calvidev.github.io` — **DNS only** (gray cloud) |
| MX | `send` | `feedback-smtp.us-east-1....` (Resend bounce) |
| TXT | `resend._domainkey` | DKIM key (Resend) |
| TXT | `send` | SPF record (Resend) |
