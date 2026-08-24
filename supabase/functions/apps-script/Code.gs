// ── Config ────────────────────────────────────
const SHEET_ID     = '1Cfk7dx0S05TF8NbCDxdl7ofk491hmhu5SkXKoRo0uVU';
const SHEET_NAME   = 'Sheet1';
const RESEND_KEY   = '<your-resend-api-key>';  // set this in the deployed script, not here
const ADMIN_SECRET = 'CalviPresa26';
const OWNER_EMAIL  = 'presa@calvi.dev';
const FROM_EMAIL   = 'La Presa <presa@calvi.dev>';

// ── Sheet helper ──────────────────────────────
function getSheet() {
  return SpreadsheetApp.openById(SHEET_ID).getSheetByName(SHEET_NAME);
}

// ── CORS headers ──────────────────────────────
function cors(output) {
  return output
    .setMimeType(ContentService.MimeType.JSON);
}

function json(data) {
  return cors(ContentService.createTextOutput(JSON.stringify(data)));
}

// ── GET — return all bookings ─────────────────
function doGet() {
  const sheet = getSheet();
  const rows  = sheet.getDataRange().getValues();
  if (rows.length <= 1) return json([]);

  const bookings = rows.slice(1)
    .filter(r => r[0] !== '')
    .map(r => ({
      id:         String(r[0]),
      name:       r[1],
      email:      r[2],
      start_date: r[3],
      end_date:   r[4],
      created_at: r[5]
    }));

  return json(bookings);
}

// ── POST — add / delete ───────────────────────
function doPost(e) {
  const data = JSON.parse(e.postData.contents);

  if (data.action === 'add')    return addBooking(data);
  if (data.action === 'delete') return deleteBooking(data);
  if (data.action === 'manual') return addManual(data);

  return json({ error: 'Unknown action' });
}

// ── Add booking (guest) ───────────────────────
function addBooking(data) {
  const sheet = getSheet();
  const id    = Date.now().toString();
  const now   = new Date().toISOString();

  sheet.appendRow([id, data.name, data.email, data.start_date, data.end_date, now]);

  sendEmail(data.email, 'Reservación confirmada · La Presa',
    confirmationHtml(data.name, data.email, data.start_date, data.end_date));
  sendEmail(OWNER_EMAIL, 'Nueva reservación: ' + data.name,
    ownerHtml(data.name, data.email, data.start_date, data.end_date));

  return json({ ok: true, id });
}

// ── Add manual booking (admin) ────────────────
function addManual(data) {
  if (data.secret !== ADMIN_SECRET) return json({ error: 'Unauthorized' });

  const sheet = getSheet();
  const id    = Date.now().toString();
  const now   = new Date().toISOString();

  sheet.appendRow([id, data.name, data.email || '—', data.start_date, data.end_date, now]);
  return json({ ok: true, id });
}

// ── Delete booking ────────────────────────────
function deleteBooking(data) {
  if (data.secret !== ADMIN_SECRET) return json({ error: 'Unauthorized' });

  const sheet = getSheet();
  const rows  = sheet.getDataRange().getValues();

  for (let i = 1; i < rows.length; i++) {
    if (String(rows[i][0]) === String(data.id)) {
      const [, name, email, start, end] = rows[i];
      if (email && email !== '—') {
        sendEmail(email, 'Reservación cancelada · La Presa',
          cancellationHtml(name, start, end));
      }
      sheet.deleteRow(i + 1);
      return json({ ok: true });
    }
  }

  return json({ error: 'Not found' });
}

// ── Send email via Resend ─────────────────────
function sendEmail(to, subject, html) {
  UrlFetchApp.fetch('https://api.resend.com/emails', {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + RESEND_KEY },
    payload: JSON.stringify({ from: FROM_EMAIL, to, subject, html }),
    muteHttpExceptions: true
  });
}

// ── Email helpers ─────────────────────────────
function fmtDate(iso) {
  return new Date(iso + 'T12:00:00').toLocaleDateString('es-MX', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
}

function nights(start, end) {
  return Math.round((new Date(end + 'T12:00:00') - new Date(start + 'T12:00:00')) / 86400000);
}

function baseStyle() {
  return 'font-family:Georgia,serif;background:#F2EDE4;margin:0;padding:40px 20px;color:#1C3A2A;';
}

function cardStyle() {
  return 'max-width:480px;margin:0 auto;background:#EDE7DC;padding:40px 36px;';
}

function confirmationHtml(name, email, start, end) {
  const first = name.split(' ')[0];
  const n = nights(start, end);
  return `<html><body style="${baseStyle()}"><div style="${cardStyle()}">
    <h1 style="font-size:1.6rem;font-weight:400;letter-spacing:.05em;margin:0 0 8px">La Presa</h1>
    <p style="font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;opacity:.55;margin-bottom:32px">Calvi Family · Summer Home</p>
    <p style="font-size:.95rem;line-height:1.6">Hola ${first}, tu estadía ha quedado reservada. Nos vemos pronto.</p>
    <hr style="border:none;border-top:1px solid #C8BCA8;margin:24px 0">
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Llegada</p>
    <p style="font-size:.95rem;margin-bottom:14px">${fmtDate(start)}</p>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Salida</p>
    <p style="font-size:.95rem;margin-bottom:14px">${fmtDate(end)}</p>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Noches</p>
    <p style="font-size:.95rem">${n}</p>
    <hr style="border:none;border-top:1px solid #C8BCA8;margin:24px 0">
    <p style="font-size:.82rem;opacity:.6;line-height:1.6">¿Preguntas? Responde este correo.</p>
    <p style="margin-top:36px;font-size:.72rem;opacity:.45;letter-spacing:.08em">presa.calvi.dev</p>
  </div></body></html>`;
}

function ownerHtml(name, email, start, end) {
  return `<html><body style="${baseStyle()}"><div style="${cardStyle()}">
    <h1 style="font-size:1.4rem;font-weight:400;margin:0 0 24px">Nueva reservación · La Presa</h1>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Nombre</p>
    <p style="font-size:.95rem;margin-bottom:14px">${name}</p>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Email</p>
    <p style="font-size:.95rem;margin-bottom:14px">${email}</p>
    <hr style="border:none;border-top:1px solid #C8BCA8;margin:20px 0">
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Llegada</p>
    <p style="font-size:.95rem;margin-bottom:14px">${fmtDate(start)}</p>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Salida</p>
    <p style="font-size:.95rem">${fmtDate(end)}</p>
  </div></body></html>`;
}

function cancellationHtml(name, start, end) {
  const first = name.split(' ')[0];
  return `<html><body style="${baseStyle()}"><div style="${cardStyle()}">
    <h1 style="font-size:1.6rem;font-weight:400;letter-spacing:.05em;margin:0 0 8px">La Presa</h1>
    <p style="font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;opacity:.55;margin-bottom:32px">Calvi Family · Summer Home</p>
    <p style="font-size:.95rem;line-height:1.6">Hola ${first}, te informamos que tu reservación ha sido cancelada. Si tienes preguntas, responde este correo.</p>
    <hr style="border:none;border-top:1px solid #C8BCA8;margin:24px 0">
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Llegada</p>
    <p style="font-size:.95rem;margin-bottom:14px">${fmtDate(start)}</p>
    <p style="font-size:.7rem;letter-spacing:.15em;text-transform:uppercase;opacity:.55;margin-bottom:4px">Salida</p>
    <p style="font-size:.95rem">${fmtDate(end)}</p>
    <hr style="border:none;border-top:1px solid #C8BCA8;margin:24px 0">
    <p style="font-size:.82rem;opacity:.6;line-height:1.6">Esperamos verte pronto en La Presa.</p>
    <p style="margin-top:36px;font-size:.72rem;opacity:.45;letter-spacing:.08em">presa.calvi.dev</p>
  </div></body></html>`;
}
