# Handoff: deploy `calvi.dev/mexico` (World Cup 2026 bracket page)

Paste this whole file as your first message in the new Claude Code session.
It contains everything needed to finish the job — no need to re-derive context.

---

## Context

This is a side task for the Calvi family. The main site is **La Presa**
(`presa.calvi.dev`, repo `calvidev/presa`) — a booking calendar for the family's
summer home, built as vanilla HTML/CSS/JS on GitHub Pages, with Cloudflare DNS
in front of it (`calvi.dev` domain).

A new, separate page was built to track **Mexico's run through the 2026 FIFA
World Cup** — group standings, road to the final, and possible knockout
opponents — with **live data** (no backend, no API key). The user
(`jccalvih@gmail.com`) wants this page served at the **apex/root domain**:
**`calvi.dev/mexico`** — *not* on the `presa.` subdomain.

The existing `calvidev/presa` repo can't do this: its `CNAME` file is pinned to
`presa.calvi.dev`, and a GitHub Pages site can only be bound to one custom
domain. So the user created a **new, separate repo** for this:

**Target repo: `Calvidev/ysisi`** — https://github.com/Calvidev/ysisi.git

This repo needs to be set up from scratch as a GitHub Pages site bound to the
apex domain `calvi.dev`, serving the bracket page at the `/mexico` path.

---

## What to do

### 1. In the `Calvidev/ysisi` repo

- Add a `CNAME` file at the repo root containing exactly:
  ```
  calvi.dev
  ```
- Add the bracket page at **`mexico/index.html`** (so it serves cleanly at
  `calvi.dev/mexico` / `calvi.dev/mexico/`). The full, already-built and
  tested file content is below — copy it verbatim.
- Copy the family's `logo.jpg` from `calvidev/presa` (used as the favicon) to
  the root of `Calvidev/ysisi`, since the HTML below references it as
  `/logo.jpg` (absolute path, so it resolves correctly regardless of the page
  being nested under `/mexico/`). If you don't have access to fetch it from
  `calvidev/presa`, it's fine to drop that `<link rel="icon">` line instead —
  it's cosmetic only.
- Add a root `index.html` if the repo doesn't have one yet (GitHub Pages
  needs *something* at the root). A minimal redirect or placeholder is fine
  unless the user has other plans for `calvi.dev` itself — ask them if
  unsure, don't guess at unrelated content for the root domain.
- Commit and push to whichever branch GitHub Pages will build from (check
  repo settings — likely `main`).
- In **Settings → Pages** for `Calvidev/ysisi`:
  - Source: deploy from branch (the branch you pushed to), root folder.
  - Custom domain: enter `calvi.dev` and save (GitHub will detect the CNAME
    file too).
  - Wait for DNS to verify, then enable **"Enforce HTTPS"** once it becomes
    available (certificate provisioning can take a few minutes to a few
    hours after DNS propagates — don't worry if it's greyed out at first).

### 2. DNS changes (Cloudflare) — the user needs to do this themselves

Tell the user to add these records in Cloudflare for `calvi.dev` (apex
record, i.e. `@`), matching the pattern already used for `presa` (DNS-only /
gray cloud, **not proxied** — GitHub Pages requires this):

| Type | Name | Value | Proxy status |
|---|---|---|---|
| A | `@` | `185.199.108.153` | DNS only |
| A | `@` | `185.199.109.153` | DNS only |
| A | `@` | `185.199.110.153` | DNS only |
| A | `@` | `185.199.111.153` | DNS only |
| AAAA | `@` | `2606:50c0:8000::153` | DNS only (optional) |
| AAAA | `@` | `2606:50c0:8001::153` | DNS only (optional) |
| AAAA | `@` | `2606:50c0:8002::153` | DNS only (optional) |
| AAAA | `@` | `2606:50c0:8003::153` | DNS only (optional) |

If there's already an existing `@`/apex record in Cloudflare (e.g. pointing
somewhere else, or a redirect), check with the user before removing it —
don't just overwrite blind.

### 3. Verify

Once DNS propagates and Pages finishes building, confirm `calvi.dev/mexico`
loads the page and the live data fetch works (open browser dev tools, check
no CORS/network errors on the `raw.githubusercontent.com` request).

---

## The page: `mexico/index.html`

This file is fully built and was validated against real 2026 World Cup
schedule data before being committed. It fetches
`https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`
client-side (free, no API key, CORS-enabled, updated ~daily by the dataset
maintainer) and computes:

- Mexico's Group A standings table (live)
- A "road to the final" timeline (group stage → R32 → R16 → QF → SF → Final)
  with dates/venues, marking completed rounds and showing the actual or
  probable opponent at each stage
- The 5 candidate groups (C, E, F, H, I) whose 3rd-place teams could be
  Mexico's Round-of-32 opponent (Mexico is projected as Group A's #1 seed,
  per the "best 3rd-place" bracket rule)

If the live fetch fails, it falls back to a static snapshot (dated 19 June
2026) embedded directly in the HTML, so the page never breaks even offline.

Copy everything between the markers below into `mexico/index.html` exactly
as-is:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>México · Mundial 2026</title>
  <link rel="icon" href="/logo.jpg" type="image/jpeg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Inter:wght@300;400&display=swap" rel="stylesheet">
  <style>
    :root {
      --green:  #1C3A2A;
      --green2: #2E5740;
      --cream:  #F2EDE4;
      --paper:  #EDE7DC;
      --border: #C8BCA8;
      --muted:  rgba(28,58,42,0.45);
      --gold:   #A67C2E;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: var(--cream);
      color: var(--green);
      font-family: 'Inter', sans-serif;
      font-weight: 300;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    header {
      padding: 56px 24px 0;
      text-align: center;
    }

    h1 {
      font-family: 'Cormorant Garamond', serif;
      font-weight: 300;
      font-size: 2.4rem;
      letter-spacing: 0.06em;
      line-height: 1;
    }

    .tagline {
      font-size: 0.68rem;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: var(--muted);
      margin-top: 10px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 22px;
      padding: 8px 18px;
      background: var(--green);
      color: var(--cream);
      font-size: 0.66rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    .status-pill .dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--gold);
    }

    .rule {
      width: 1px;
      height: 32px;
      background: var(--border);
      margin: 28px auto;
    }

    main {
      width: 100%;
      max-width: 620px;
      padding: 0 24px 60px;
    }

    .section-label {
      font-size: 0.65rem;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 18px;
    }

    section { margin-bottom: 48px; }

    /* ── Grupo A table ───────────────────────── */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.78rem;
    }

    thead th {
      text-align: center;
      font-size: 0.6rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      padding: 0 4px 10px;
      font-weight: 400;
    }
    thead th:first-child { text-align: left; }

    tbody td {
      text-align: center;
      padding: 10px 4px;
      border-top: 1px solid var(--border);
    }
    tbody td:first-child {
      text-align: left;
      font-weight: 400;
    }

    tr.mex td { color: var(--green); font-weight: 400; background: rgba(28,58,42,0.05); }
    tr.mex td:first-child { border-left: 2px solid var(--green); padding-left: 10px; }

    .pts { font-weight: 400; }

    .group-note {
      margin-top: 16px;
      font-size: 0.76rem;
      color: var(--green2);
      line-height: 1.5;
    }
    .group-note .next {
      display: block;
      margin-top: 8px;
      padding: 10px 14px;
      background: rgba(28,58,42,0.06);
      border-left: 2px solid var(--gold);
      font-size: 0.76rem;
    }

    /* ── Camino a la final ──────────────────── */
    .road {
      position: relative;
      padding-left: 28px;
    }
    .road::before {
      content: '';
      position: absolute;
      left: 5px; top: 6px; bottom: 6px;
      width: 1px;
      background: var(--border);
    }

    .step {
      position: relative;
      padding-bottom: 28px;
    }
    .step:last-child { padding-bottom: 0; }

    .step::before {
      content: '';
      position: absolute;
      left: -28px; top: 3px;
      width: 9px; height: 9px;
      border-radius: 50%;
      background: var(--cream);
      border: 1px solid var(--green);
    }
    .step.done::before { background: var(--green); }

    .step-round {
      font-family: 'Cormorant Garamond', serif;
      font-size: 1.1rem;
      font-weight: 400;
      letter-spacing: 0.02em;
    }

    .step-meta {
      font-size: 0.7rem;
      color: var(--muted);
      letter-spacing: 0.04em;
      margin-top: 4px;
    }

    .step-rival {
      font-size: 0.8rem;
      color: var(--green2);
      margin-top: 6px;
      line-height: 1.5;
    }

    .step-rival .tbd {
      color: var(--muted);
      font-style: italic;
    }

    /* ── Candidatos a rival ──────────────────── */
    .candidates {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin-top: 18px;
    }
    .candidate-group {
      border: 1px solid var(--border);
      background: var(--paper);
      padding: 12px 14px;
    }
    .candidate-group .g-label {
      font-size: 0.6rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .candidate-group .g-teams {
      font-size: 0.78rem;
      line-height: 1.5;
    }

    .candidates-note {
      margin-top: 14px;
      font-size: 0.72rem;
      color: var(--muted);
      line-height: 1.5;
    }

    footer {
      margin-top: auto;
      padding: 32px 24px 40px;
      text-align: center;
      font-size: 0.6rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
    }

    @media (max-width: 480px) {
      header { padding: 36px 20px 0; }
      h1 { font-size: 2rem; }
      main { padding: 0 18px 48px; }
      .candidates { grid-template-columns: 1fr; }
      table { font-size: 0.72rem; }
    }
  </style>
</head>
<body>

<header>
  <h1>México</h1>
  <p class="tagline">Mundial 2026 &middot; Camino a la final</p>
  <div class="status-pill" id="statusPill"><span class="dot"></span>Líder del Grupo A</div>
</header>

<div class="rule"></div>

<main>

  <section>
    <p class="section-label">Grupo A</p>
    <table>
      <thead>
        <tr>
          <th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DG</th><th>Pts</th>
        </tr>
      </thead>
      <tbody id="groupBody">
        <tr class="mex">
          <td>México</td><td>2</td><td>2</td><td>0</td><td>0</td><td>3</td><td>0</td><td>+3</td><td class="pts">6</td>
        </tr>
        <tr>
          <td>Corea del Sur</td><td>2</td><td>1</td><td>0</td><td>1</td><td>2</td><td>2</td><td>0</td><td class="pts">3</td>
        </tr>
        <tr>
          <td>Chequia</td><td>2</td><td>0</td><td>1</td><td>1</td><td>2</td><td>3</td><td>-1</td><td class="pts">1</td>
        </tr>
        <tr>
          <td>Sudáfrica</td><td>2</td><td>0</td><td>1</td><td>1</td><td>1</td><td>3</td><td>-2</td><td class="pts">1</td>
        </tr>
      </tbody>
    </table>
    <p class="group-note" id="groupNote">
      México venció 2-0 a Sudáfrica (11 jun) y 1-0 a Corea del Sur (18 jun), asegurando matemáticamente el primer lugar del grupo.
      Corea del Sur venció 2-1 a Chequia en la J1; Chequia y Sudáfrica empataron 1-1 en la J2.
      <span class="next">Próximo partido (J3): México vs. Chequia · miércoles 24 de junio · Estadio Azteca, CDMX</span>
    </p>
  </section>

  <section>
    <p class="section-label">Camino a la final</p>
    <div class="road">

      <div class="step done" id="step-groups">
        <div class="step-round">Fase de grupos</div>
        <div class="step-meta">11 — 24 jun &middot; sedes del Grupo A</div>
        <div class="step-rival" id="rival-groups">Líder de grupo asegurado tras la J2. Falta el cierre vs. Chequia.</div>
      </div>

      <div class="step" id="step-r32">
        <div class="step-round">Dieciseisavos de final</div>
        <div class="step-meta">Martes 30 de junio &middot; Estadio Azteca, CDMX</div>
        <div class="step-rival" id="rival-r32">
          Rival: el mejor tercer lugar entre los Grupos C, E, F, H o I
          <span class="tbd">(se define hasta el 27 de junio, al cerrar la fase de grupos)</span>
        </div>
      </div>

      <div class="step" id="step-r16">
        <div class="step-round">Octavos de final</div>
        <div class="step-meta">Domingo 5 de julio &middot; Estadio Azteca, CDMX</div>
        <div class="step-rival" id="rival-r16"><span class="tbd">Rival por definir — depende del resultado en dieciseisavos</span></div>
      </div>

      <div class="step" id="step-qf">
        <div class="step-round">Cuartos de final</div>
        <div class="step-meta">Sábado 11 de julio &middot; Miami</div>
        <div class="step-rival" id="rival-qf"><span class="tbd">Rival por definir</span></div>
      </div>

      <div class="step" id="step-sf">
        <div class="step-round">Semifinal</div>
        <div class="step-meta">Miércoles 15 de julio &middot; Atlanta</div>
        <div class="step-rival" id="rival-sf"><span class="tbd">Rival por definir</span></div>
      </div>

      <div class="step" id="step-final">
        <div class="step-round">Final</div>
        <div class="step-meta">Domingo 19 de julio &middot; MetLife Stadium, East Rutherford, NJ</div>
        <div class="step-rival" id="rival-final"><span class="tbd">Rival por definir</span></div>
      </div>

    </div>
  </section>

  <section>
    <p class="section-label">Posibles rivales en dieciseisavos</p>
    <div class="candidates" id="candidatesGrid">
      <div class="candidate-group">
        <div class="g-label">Grupo C</div>
        <div class="g-teams">Brasil, Marruecos, Haití, Escocia</div>
      </div>
      <div class="candidate-group">
        <div class="g-label">Grupo E</div>
        <div class="g-teams">Alemania, Curazao, Costa de Marfil, Ecuador</div>
      </div>
      <div class="candidate-group">
        <div class="g-label">Grupo F</div>
        <div class="g-teams">Países Bajos, Japón, Suecia, Túnez</div>
      </div>
      <div class="candidate-group">
        <div class="g-label">Grupo H</div>
        <div class="g-teams">España, Cabo Verde, Arabia Saudita, Uruguay</div>
      </div>
      <div class="candidate-group">
        <div class="g-label">Grupo I</div>
        <div class="g-teams">Francia, Senegal, Irak, Noruega</div>
      </div>
    </div>
    <p class="candidates-note">
      Como líder del Grupo A, el rival de México en dieciseisavos será el equipo que termine como el mejor tercer lugar
      entre estos cinco grupos (regla de los "8 mejores terceros"). Aún no se sabe qué equipo será — depende de cómo
      terminen sus respectivas fases de grupos.
    </p>
  </section>

</main>

<footer id="footerNote">Datos en vivo &middot; calvi.dev/mexico</footer>

<script>
  // ── Live data source ───────────────────────
  // Free, open, no API key needed. Updated ~daily by the maintainer.
  // https://github.com/openfootball/worldcup.json
  const SRC = 'https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json';
  const MEXICO = 'Mexico';
  const GROUP = 'Group A';

  const MONTHS_ES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];

  function fmtDateEs(iso) {
    const [y, m, d] = iso.split('-').map(Number);
    return `${d} de ${MONTHS_ES[m - 1]}`;
  }

  function parseKickoffUTC(m) {
    const tm = /(\d+):(\d+)\s*UTC([+-]\d+)/.exec(m.time || '12:00 UTC+0');
    const [, hh, mm, off] = tm ? tm : [null, '12', '00', '0'];
    const [y, mo, d] = m.date.split('-').map(Number);
    return new Date(Date.UTC(y, mo - 1, d, Number(hh) - Number(off), Number(mm)));
  }

  function describeSlot(code) {
    if (!code) return 'por definir';
    let m = /^([12])([A-L])$/.exec(code);
    if (m) return (m[1] === '1' ? 'Líder' : '2º lugar') + ' del Grupo ' + m[2];
    m = /^3((?:[A-L]\/?)+)$/.exec(code);
    if (m) return 'mejor 3º (Grupos ' + m[1].split('/').join(', ') + ')';
    return code; // ya es un equipo real
  }

  function opponentLabel(code, byNum) {
    const m = /^W(\d+)$/.exec(code || '');
    if (m && byNum[m[1]]) {
      const ref = byNum[m[1]];
      return 'el ganador entre ' + describeSlot(ref.team1) + ' y ' + describeSlot(ref.team2);
    }
    return describeSlot(code);
  }

  function buildGroupTable(matches) {
    const groupMatches = matches.filter(m => m.group === GROUP);
    const teams = {};
    const ensure = name => teams[name] || (teams[name] = { name, pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0 });

    groupMatches.forEach(m => { ensure(m.team1); ensure(m.team2); });

    groupMatches.forEach(m => {
      if (!m.score || !m.score.ft) return;
      const [s1, s2] = m.score.ft;
      const t1 = ensure(m.team1), t2 = ensure(m.team2);
      t1.pj++; t2.pj++;
      t1.gf += s1; t1.gc += s2;
      t2.gf += s2; t2.gc += s1;
      if (s1 > s2) { t1.g++; t2.p++; }
      else if (s1 < s2) { t2.g++; t1.p++; }
      else { t1.e++; t2.e++; }
    });

    const table = Object.values(teams).map(t => ({ ...t, dg: t.gf - t.gc, pts: t.g * 3 + t.e }));
    table.sort((a, b) => b.pts - a.pts || b.dg - a.dg || b.gf - a.gf);

    const tbody = document.getElementById('groupBody');
    tbody.innerHTML = table.map(t => `
      <tr class="${t.name === MEXICO ? 'mex' : ''}">
        <td>${t.name === MEXICO ? 'México' : t.name}</td>
        <td>${t.pj}</td><td>${t.g}</td><td>${t.e}</td><td>${t.p}</td>
        <td>${t.gf}</td><td>${t.gc}</td><td>${t.dg > 0 ? '+' + t.dg : t.dg}</td>
        <td class="pts">${t.pts}</td>
      </tr>`).join('');

    const played = groupMatches.filter(m => m.score && m.score.ft);
    const pending = groupMatches.filter(m => !m.score || !m.score.ft)
      .sort((a, b) => parseKickoffUTC(a) - parseKickoffUTC(b));

    const summaryParts = played
      .filter(m => m.team1 === MEXICO || m.team2 === MEXICO)
      .map(m => {
        const [s1, s2] = m.score.ft;
        const opp = m.team1 === MEXICO ? m.team2 : m.team1;
        const score = m.team1 === MEXICO ? `${s1}-${s2}` : `${s2}-${s1}`;
        return `${score} vs. ${opp === MEXICO ? '' : opp} (${fmtDateEs(m.date)})`.replace('vs. (', '(');
      });

    const top = table[0];
    let html = top
      ? (top.name === MEXICO
          ? `México ${summaryParts.length ? 'venció ' + summaryParts.join(' y ') : 'lidera el Grupo A'} (${top.pts} pts, ${played.filter(m=>m.team1===MEXICO||m.team2===MEXICO).length}/${groupMatches.filter(m=>m.team1===MEXICO||m.team2===MEXICO).length} jugados).`
          : `México va en el ${table.findIndex(t => t.name === MEXICO) + 1}º lugar del Grupo A con ${teams[MEXICO] ? ensure(MEXICO).pts : 0} pts.`)
      : 'Cargando standings del Grupo A…';

    const nextMex = pending.find(m => m.team1 === MEXICO || m.team2 === MEXICO);
    if (nextMex) {
      const opp = nextMex.team1 === MEXICO ? nextMex.team2 : nextMex.team1;
      html += `<span class="next">Próximo partido: México vs. ${opp} · ${fmtDateEs(nextMex.date)} · ${nextMex.ground}</span>`;
    } else if (pending.length === 0) {
      html += `<span class="next">Fase de grupos completa.</span>`;
    }
    document.getElementById('groupNote').innerHTML = html;

    return { table, allPlayed: pending.length === 0, mexicoTop: top && top.name === MEXICO };
  }

  function buildKnockoutChain(matches) {
    const numbered = matches.slice().sort((a, b) => parseKickoffUTC(a) - parseKickoffUTC(b));
    numbered.forEach((m, i) => { m._num = i + 1; });
    const byNum = {};
    numbered.forEach(m => { byNum[m._num] = m; });

    const rounds = [
      ['Round of 32', 'rival-r32', 'step-r32'],
      ['Round of 16', 'rival-r16', 'step-r16'],
      ['Quarter-final', 'rival-qf', 'step-qf'],
      ['Semi-final', 'rival-sf', 'step-sf'],
      ['Final', 'rival-final', 'step-final'],
    ];

    let refs = new Set([MEXICO, '1A']);
    let eliminated = false;

    rounds.forEach(([roundName, rivalId, stepId]) => {
      const stepEl = document.getElementById(stepId);
      const rivalEl = document.getElementById(rivalId);
      if (eliminated) {
        rivalEl.innerHTML = '<span class="tbd">México no llegó a esta ronda</span>';
        return;
      }

      const m = numbered.find(x => x.round === roundName && (refs.has(x.team1) || refs.has(x.team2)));
      if (!m) {
        rivalEl.innerHTML = '<span class="tbd">Rival por definir</span>';
        return;
      }

      const ourSide = refs.has(m.team1) ? 'team1' : 'team2';
      const oppSide = ourSide === 'team1' ? 'team2' : 'team1';
      const oppCode = m[oppSide];

      if (m.score && m.score.ft) {
        const [sUs, sOpp] = ourSide === 'team1' ? m.score.ft : m.score.ft.slice().reverse();
        const result = sUs > sOpp ? 'México avanza' : sUs < sOpp ? 'México queda eliminado' : 'Empate';
        rivalEl.innerHTML = `Rival: <strong>${describeSlot(oppCode)}</strong> · Resultado: ${sUs}-${sOpp} · ${result}`;
        stepEl.classList.add('done');
        if (sUs < sOpp) eliminated = true;
        refs = new Set([MEXICO]);
      } else {
        rivalEl.innerHTML = `Rival: ${opponentLabel(oppCode, byNum)} <span class="tbd">(por jugarse)</span>`;
        refs = new Set([MEXICO, 'W' + m._num]);
      }
    });
  }

  function buildCandidates(matches) {
    const groups = ['C', 'E', 'F', 'H', 'I'];
    const grid = document.getElementById('candidatesGrid');
    grid.innerHTML = groups.map(letter => {
      const groupName = 'Group ' + letter;
      const teamSet = new Set();
      matches.filter(m => m.group === groupName).forEach(m => { teamSet.add(m.team1); teamSet.add(m.team2); });
      return `<div class="candidate-group">
        <div class="g-label">Grupo ${letter}</div>
        <div class="g-teams">${[...teamSet].join(', ') || '—'}</div>
      </div>`;
    }).join('');
  }

  async function loadLiveData() {
    const res = await fetch(SRC, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const matches = data.matches;

    const { mexicoTop } = buildGroupTable(matches);
    buildKnockoutChain(matches);
    buildCandidates(matches);

    const pill = document.getElementById('statusPill');
    pill.innerHTML = '<span class="dot"></span>' + (mexicoTop ? 'Líder del Grupo A' : 'Siguiendo al Grupo A');

    document.getElementById('footerNote').textContent =
      'Datos en vivo (openfootball/worldcup.json) · actualizado ' + new Date().toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
  }

  loadLiveData().catch(err => {
    console.error('No se pudieron cargar datos en vivo:', err);
    document.getElementById('footerNote').textContent =
      'Sin conexión a datos en vivo — mostrando el último snapshot conocido (19 de junio, 2026) · calvi.dev/mexico';
  });
</script>

</body>
</html>
```

---

## Notes / things to flag back to the user if relevant

- The fallback static snapshot in the table above is dated **19 June 2026**.
  If real time has moved past that and the live fetch is broken for some
  reason, the fallback will look stale — that's expected/acceptable
  behavior (it's just a safety net), not a bug to fix.
- This page was originally built and is also sitting, committed, at
  `mexico.html` on branch `claude/world-cup-brackets-live-g2rc2o` in the
  `calvidev/presa` repo. That copy can stay there or be removed later —
  it's not linked from `index.html` and doesn't affect `presa.calvi.dev`
  either way. No action needed on that repo as part of this task.
- Don't touch `calvidev/presa`'s own `CNAME` (`presa.calvi.dev`) — that
  binding must stay intact for the booking site to keep working.
