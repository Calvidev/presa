const RESEND_KEY = Deno.env.get('RESEND_API_KEY')!

function fmt(iso: string): string {
  return new Date(iso + 'T12:00:00').toLocaleDateString('es-MX', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  })
}

Deno.serve(async (req) => {
  try {
    const { name, email, start_date, end_date } = await req.json()
    const firstName = name.split(' ')[0]

    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${RESEND_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'La Presa <presa@calvi.dev>',
        to: email,
        subject: 'Reservación cancelada · La Presa',
        html: `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<style>
  body { font-family: Georgia, serif; background: #F2EDE4; margin: 0; padding: 40px 20px; color: #1C3A2A; }
  .card { max-width: 480px; margin: 0 auto; background: #EDE7DC; padding: 40px 36px; }
  h1 { font-size: 1.6rem; font-weight: 400; letter-spacing: 0.05em; margin: 0 0 8px; }
  .sub { font-size: 0.72rem; letter-spacing: 0.22em; text-transform: uppercase; opacity: 0.55; margin-bottom: 32px; }
  .rule { border: none; border-top: 1px solid #C8BCA8; margin: 24px 0; }
  .label { opacity: 0.55; font-size: 0.7rem; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 4px; }
  .val { font-size: 0.95rem; margin-bottom: 14px; }
  .footer { margin-top: 36px; font-size: 0.72rem; opacity: 0.45; letter-spacing: 0.08em; }
</style>
</head>
<body>
<div class="card">
  <h1>La Presa</h1>
  <p class="sub">Calvi Family · Summer Home</p>
  <p style="font-size:0.95rem;line-height:1.6;">
    Hola ${firstName}, te informamos que tu reservación ha sido cancelada.
    Si crees que esto es un error o tienes preguntas, responde este correo.
  </p>
  <hr class="rule">
  <div><p class="label">Llegada</p><p class="val">${fmt(start_date)}</p></div>
  <div><p class="label">Salida</p><p class="val">${fmt(end_date)}</p></div>
  <hr class="rule">
  <p style="font-size:0.82rem;opacity:0.6;line-height:1.6;">
    Esperamos verte pronto en La Presa.
  </p>
  <p class="footer">presa.calvi.dev</p>
</div>
</body>
</html>`,
      }),
    })

    if (!res.ok) throw new Error(await res.text())

    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (err) {
    console.error(err)
    return new Response(JSON.stringify({ error: String(err) }), { status: 500 })
  }
})
