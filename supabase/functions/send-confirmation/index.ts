const RESEND_KEY = Deno.env.get('RESEND_API_KEY')!

function fmt(iso: string): string {
  return new Date(iso + 'T12:00:00').toLocaleDateString('es-MX', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  })
}

function nights(start: string, end: string): number {
  return Math.round(
    (new Date(end + 'T12:00:00').getTime() - new Date(start + 'T12:00:00').getTime())
    / 86_400_000
  )
}

async function sendEmail(to: string, subject: string, html: string) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from: 'La Presa <presa@calvi.dev>', to, subject, html }),
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Resend error: ${err}`)
  }
}

Deno.serve(async (req) => {
  try {
    const { record } = await req.json()
    const { name, email, start_date, end_date } = record
    const firstName = name.split(' ')[0]
    const n = nights(start_date, end_date)

    // ── Email al huésped ──────────────────────
    await sendEmail(
      email,
      'Reservación confirmada · La Presa',
      `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<style>
  body { font-family: Georgia, serif; background: #F2EDE4; margin: 0; padding: 40px 20px; color: #1C3A2A; }
  .card { max-width: 480px; margin: 0 auto; background: #EDE7DC; padding: 40px 36px; }
  h1 { font-size: 1.6rem; font-weight: 400; letter-spacing: 0.05em; margin: 0 0 8px; }
  .sub { font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase; opacity: 0.55; margin-bottom: 32px; }
  .rule { border: none; border-top: 1px solid #C8BCA8; margin: 24px 0; }
  .row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.88rem; }
  .label { opacity: 0.55; font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase; }
  .val { font-size: 0.95rem; }
  .footer { margin-top: 36px; font-size: 0.72rem; opacity: 0.45; letter-spacing: 0.08em; }
</style>
</head>
<body>
<div class="card">
  <h1>La Presa</h1>
  <p class="sub">Calvi Family · Summer Home</p>
  <p style="font-size:0.95rem;line-height:1.6;">Hola ${firstName}, tu estadía ha quedado reservada. Nos vemos pronto.</p>
  <hr class="rule">
  <div>
    <p class="label">Llegada</p>
    <p class="val">${fmt(start_date)}</p>
  </div>
  <div style="margin-top:14px;">
    <p class="label">Salida</p>
    <p class="val">${fmt(end_date)}</p>
  </div>
  <div style="margin-top:14px;">
    <p class="label">Noches</p>
    <p class="val">${n}</p>
  </div>
  <hr class="rule">
  <p style="font-size:0.82rem;opacity:0.6;line-height:1.6;">
    ¿Preguntas? Responde este correo y con gusto te ayudamos.
  </p>
  <p class="footer">presa.calvi.dev</p>
</div>
</body>
</html>`
    )

    // ── Notificación al dueño ─────────────────
    await sendEmail(
      'presa@calvi.dev',
      `Nueva reservación: ${name}`,
      `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<style>
  body { font-family: Georgia, serif; background: #F2EDE4; margin: 0; padding: 40px 20px; color: #1C3A2A; }
  .card { max-width: 480px; margin: 0 auto; background: #EDE7DC; padding: 40px 36px; }
  h1 { font-size: 1.4rem; font-weight: 400; margin: 0 0 24px; }
  .rule { border: none; border-top: 1px solid #C8BCA8; margin: 20px 0; }
  .label { opacity: 0.55; font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 4px; }
  .val { font-size: 0.95rem; margin-bottom: 14px; }
</style>
</head>
<body>
<div class="card">
  <h1>Nueva reservación · La Presa</h1>
  <div><p class="label">Nombre</p><p class="val">${name}</p></div>
  <div><p class="label">Email</p><p class="val">${email}</p></div>
  <hr class="rule">
  <div><p class="label">Llegada</p><p class="val">${fmt(start_date)}</p></div>
  <div><p class="label">Salida</p><p class="val">${fmt(end_date)}</p></div>
  <div><p class="label">Noches</p><p class="val">${n}</p></div>
</div>
</body>
</html>`
    )

    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err) {
    console.error(err)
    return new Response(JSON.stringify({ error: String(err) }), { status: 500 })
  }
})
