# La Presa · presa.calvi.dev

Booking site for the Calvi family summer home. Simple, minimalist, family-only.

---

## Stack

| Layer | Service |
|---|---|
| Frontend | Vanilla HTML/CSS/JS — `index.html` + `admin.html` |
| Hosting | GitHub Pages → `presa.calvi.dev` |
| Database | Supabase (Postgres) |
| Email | Resend → `presa@calvi.dev` |
| Email routing | Cloudflare Email Routing → forwards to `jccalvih@gmail.com` |
| DNS | Cloudflare (`calvi.dev`) |

---

## How it works

### Guest flow
1. Family member visits `presa.calvi.dev`
2. Clicks a start date then an end date on the calendar
3. Fills in name + email → confirms
4. Booking saved to Supabase — calendar updates for everyone instantly
5. Resend fires two emails:
   - **Guest** → confirmation with check-in / check-out dates
   - **Owner** → notification at `presa@calvi.dev` (forwarded to Gmail)

### Admin flow
1. Owner visits `presa.calvi.dev/admin.html`
2. Logs in with `jccalvih@gmail.com` via Supabase Auth
3. Can view, cancel, or manually add bookings

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

---

## Admin dashboard

**URL:** `presa.calvi.dev/admin.html`  
**Login:** `jccalvih@gmail.com` via Supabase Auth

| Feature | Description |
|---|---|
| Stats | Upcoming reservations, total nights booked, all-time total |
| Upcoming bookings | List with name, email, dates, nights — cancel button |
| Manual booking | Add / block dates without a guest booking |
| Past bookings | Collapsible history of all past stays |

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

| Operation | Policy |
|---|---|
| `SELECT` | Public — calendar shows booked dates to everyone |
| `INSERT` | Public — anyone can create a booking |
| `DELETE` | Authenticated only — admin via Supabase Auth |

### Auth
- Provider: Email / Password
- Admin user: `jccalvih@gmail.com`

### Edge Function: `send-confirmation`
- Triggered by **Database Webhook** on `bookings INSERT`
- Sends confirmation email to guest
- Sends notification to `presa@calvi.dev`
- Secret: `RESEND_API_KEY` stored in Supabase secrets

---

## Email (Resend)

- **Domain:** `calvi.dev` (verified)
- **From address:** `presa@calvi.dev`
- **Receiving:** Cloudflare Email Routing → `jccalvih@gmail.com`
- DNS records in Cloudflare: MX + DKIM TXT + SPF TXT on `send.calvi.dev`

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
git add -p                  # stage changes
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
