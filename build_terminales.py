#!/usr/bin/env python3
"""
build_terminales.py
───────────────────
Genera terminales.html a partir de:
  - terminales.csv   (fuente de verdad de terminales)
  - qrs/             (carpeta con PNGs nombrados por serial, ej. NCCA05139588.png)

Uso:
  python build_terminales.py

Opcionales:
  python build_terminales.py --merchant "NOMBRE MERCHANT"  (override del nombre en el header)
  python build_terminales.py --password "nueva-pass"       (override de contraseña)
  python build_terminales.py --csv otra_ruta.csv           (CSV alternativo)

Configuración por defecto (editar aquí o pasar como argumento):
"""

import csv
import json
import os
import base64
import argparse
import sys

# ── Configuración por defecto ─────────────────────────────────────────────────
DEFAULT_MERCHANT  = ""          # Si está vacío, toma el campo 'negocio' del primer registro
DEFAULT_PASSWORD  = "lokal-terminales-2026"
DEFAULT_CSV       = "terminales.csv"
QR_DIR            = "qrs"
OUTPUT_FILE       = "terminales.html"
# ─────────────────────────────────────────────────────────────────────────────


def parse_args():
    p = argparse.ArgumentParser(description="Genera directorio HTML de terminales")
    p.add_argument("--merchant", default=DEFAULT_MERCHANT)
    p.add_argument("--password", default=DEFAULT_PASSWORD)
    p.add_argument("--csv",      default=DEFAULT_CSV)
    return p.parse_args()


def load_csv(path):
    if not os.path.exists(path):
        print(f"ERROR: No se encontró {path}")
        sys.exit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_qr_b64(serial):
    """Carga el PNG del QR como base64. Retorna '' si no existe."""
    path = os.path.join(QR_DIR, f"{serial}.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def bool_field(val):
    """Convierte string 'true'/'false'/'sí'/'no' a JS true/false/null."""
    v = str(val).strip().lower()
    if v in ("true", "sí", "si", "yes", "1"): return "true"
    if v in ("false", "no", "0"):              return "false"
    return "null"


def js_str(val):
    return json.dumps(str(val).strip()) if val else '""'


def build_data_js(rows):
    lines = []
    for r in rows:
        serial = r.get("serial", "").strip()
        qr_b64 = load_qr_b64(serial)
        lines.append(
            f"  {{serial:{js_str(serial)},"
            f"pos:{js_str(r.get('pos',''))},"
            f"model:{js_str(r.get('model',''))},"
            f"local:{js_str(r.get('local',''))},"
            f"negocio:{js_str(r.get('negocio',''))},"
            f"resp:{js_str(r.get('responsable',''))},"
            f"int_amex:{bool_field(r.get('int_amex',''))},"
            f"app:{js_str(r.get('app',''))},"
            f"tms:{js_str(r.get('tms',''))},"
            f"foto:{js_str(r.get('foto_dispositivo',''))},"
            f"qr:{json.dumps(qr_b64)}}}"
        )
    return "const DATA = [\n" + ",\n".join(lines) + "\n];"


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terminales · {merchant} · Lokal Money</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#F7F7F5;--surface:#FFFFFF;--border:#E2E2DC;
  --text:#1A1A18;--muted:#7A7A75;--hint:#B0B0A8;
  --green:#1E6641;--green-bg:#E4F5EC;--green-border:#B2DECA;
  --red:#B91C1C;--red-bg:#FEE8E8;--red-border:#FCBCBC;
  --amber:#92400E;--amber-bg:#FEF3C7;--amber-border:#FCD34D;
  --blue:#1D4ED8;--blue-bg:#DBEAFE;--blue-border:#93C5FD;
  --gray-bg:#F1F1EE;--gray-border:#D8D8D2;
  --mono:'IBM Plex Mono',monospace;--sans:'DM Sans',system-ui,sans-serif;
  --r-sm:8px;--r-md:12px;--r-lg:16px;
}}
[data-theme=dark]{{
  --bg:#0F0F0E;--surface:#1A1A18;--border:#2C2C28;
  --text:#F0F0EC;--muted:#888880;--hint:#555550;
  --green:#4ADE80;--green-bg:#0D3320;--green-border:#166534;
  --red:#F87171;--red-bg:#3B0A0A;--red-border:#7F1D1D;
  --amber:#FCD34D;--amber-bg:#3B1E03;--amber-border:#78350F;
  --blue:#60A5FA;--blue-bg:#1A2E4A;--blue-border:#1E40AF;
  --gray-bg:#252522;--gray-border:#3A3A35;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh;transition:background .2s,color .2s;-webkit-font-smoothing:antialiased}}

/* LOGIN */
#login-screen{{position:fixed;inset:0;background:var(--bg);display:flex;align-items:center;justify-content:center;z-index:100}}
.login-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:2.5rem 2.25rem;width:360px;box-shadow:0 4px 24px rgba(0,0,0,.06)}}
.login-brand{{display:flex;align-items:center;gap:10px;margin-bottom:2rem}}
.logo-mark{{width:34px;height:34px;border-radius:9px;background:var(--text);display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.logo-mark svg{{width:18px;height:18px}}
.login-brand .name{{font-size:15px;font-weight:600;letter-spacing:-.2px}}
.login-subtitle{{font-size:13px;color:var(--muted);margin-bottom:1.75rem;line-height:1.5}}
.field-label{{font-size:12px;font-weight:500;color:var(--muted);margin-bottom:6px;display:block}}
.pw-wrap{{position:relative;margin-bottom:.75rem}}
.pw-wrap input{{width:100%;padding:.7rem 2.75rem .7rem 1rem;border:1px solid var(--border);border-radius:var(--r-sm);font-size:14px;background:var(--bg);color:var(--text);font-family:var(--sans);outline:none;transition:border-color .15s}}
.pw-wrap input:focus{{border-color:var(--text);box-shadow:0 0 0 3px rgba(26,26,24,.08)}}
.eye-btn{{position:absolute;right:.8rem;top:50%;transform:translateY(-50%);cursor:pointer;color:var(--hint);background:none;border:none;font-size:15px;line-height:1;padding:0;transition:color .1s}}
.eye-btn:hover{{color:var(--muted)}}
.login-err{{color:var(--red);font-size:12px;margin-bottom:.75rem;display:none}}
.btn-primary{{width:100%;padding:.75rem;background:var(--text);color:var(--bg);border:none;border-radius:var(--r-sm);font-size:14px;font-weight:600;cursor:pointer;font-family:var(--sans);transition:opacity .15s}}
.btn-primary:hover{{opacity:.82}}

/* APP */
#app{{display:none}}
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:0 1.5rem;height:56px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:50}}
.h-brand{{display:flex;align-items:center;gap:8px;flex-shrink:0}}
.h-brand .logo-mark{{width:28px;height:28px;border-radius:7px}}
.h-brand .logo-mark svg{{width:14px;height:14px}}
.h-brand .name{{font-size:14px;font-weight:600}}
.h-div{{width:1px;height:18px;background:var(--border)}}
.h-title{{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.h-right{{margin-left:auto;display:flex;align-items:center;gap:6px;flex-shrink:0}}
.icon-btn{{background:none;border:1px solid var(--border);border-radius:7px;padding:.3rem .65rem;cursor:pointer;font-size:12px;color:var(--muted);font-family:var(--sans);display:flex;align-items:center;gap:5px;transition:all .1s;white-space:nowrap}}
.icon-btn:hover{{background:var(--gray-bg);color:var(--text);border-color:var(--gray-border)}}

main{{padding:1.5rem;max-width:1440px;margin:0 auto}}

.stats-bar{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1.5rem}}
.stat-pill{{background:var(--surface);border:1px solid var(--border);border-radius:99px;padding:.35rem .9rem;font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px}}
.stat-pill strong{{color:var(--text);font-weight:600}}

.toolbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}}
.search-wrap{{position:relative;flex:1;min-width:220px}}
.search-wrap svg{{position:absolute;left:.8rem;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--hint);pointer-events:none}}
.search-wrap input{{width:100%;padding:.6rem 1rem .6rem 2.4rem;border:1px solid var(--border);border-radius:var(--r-sm);font-size:13px;background:var(--surface);color:var(--text);font-family:var(--sans);outline:none;transition:border-color .15s}}
.search-wrap input:focus{{border-color:var(--text);box-shadow:0 0 0 3px rgba(26,26,24,.07)}}
.filter-select{{padding:.57rem .85rem;border:1px solid var(--border);border-radius:var(--r-sm);font-size:13px;background:var(--surface);color:var(--text);font-family:var(--sans);cursor:pointer;outline:none}}

.chips{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:1.25rem}}
.chip{{padding:5px 13px;border-radius:99px;font-size:12px;font-weight:500;border:1px solid var(--border);cursor:pointer;background:var(--surface);color:var(--muted);transition:all .12s;white-space:nowrap}}
.chip:hover{{border-color:var(--gray-border);color:var(--text);background:var(--gray-bg)}}
.chip.on{{background:var(--text);color:var(--bg);border-color:var(--text)}}
.count-line{{font-size:12px;color:var(--hint);margin-bottom:1rem}}

/* GRID */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-md);overflow:hidden;cursor:pointer;transition:box-shadow .15s,transform .12s,border-color .12s}}
.card:hover{{box-shadow:0 6px 20px rgba(0,0,0,.08);transform:translateY(-2px);border-color:var(--gray-border)}}
.card-top{{padding:1rem 1rem .85rem;background:var(--gray-bg);border-bottom:1px solid var(--border);position:relative}}
.card-badge-row{{display:flex;gap:5px;margin-bottom:.55rem;flex-wrap:wrap}}
.tag{{font-size:10px;font-weight:600;letter-spacing:.4px;padding:2px 7px;border-radius:99px;font-family:var(--mono);text-transform:uppercase}}
.tag-n950{{background:var(--blue-bg);color:var(--blue);border:1px solid var(--blue-border)}}
.tag-n750{{background:var(--green-bg);color:var(--green);border:1px solid var(--green-border)}}
.tag-n750p{{background:var(--gray-bg);color:var(--muted);border:1px solid var(--gray-border)}}
.card-serial{{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.4px;color:var(--text);margin-bottom:3px;word-break:break-all;line-height:1.3}}
.card-pos{{font-size:11px;color:var(--muted);font-family:var(--mono);min-height:15px}}
.card-body{{padding:.85rem 1rem}}
.card-local{{font-size:13px;font-weight:600;margin-bottom:.35rem}}
.card-resp{{font-size:11px;color:var(--muted);margin-bottom:.6rem;min-height:14px}}
.card-pills{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:.75rem}}
.pill{{font-size:11px;font-weight:500;padding:2px 8px;border-radius:99px;border:1px solid transparent}}
.pill-ok{{background:var(--green-bg);color:var(--green);border-color:var(--green-border)}}
.pill-no{{background:var(--gray-bg);color:var(--muted);border-color:var(--gray-border)}}
.pill-warn{{background:var(--amber-bg);color:var(--amber);border-color:var(--amber-border)}}
.pill-err{{background:var(--red-bg);color:var(--red);border-color:var(--red-border)}}
.card-qr-btn{{width:100%;padding:.45rem;border:1px dashed var(--border);border-radius:7px;font-size:11px;color:var(--muted);background:none;cursor:pointer;font-family:var(--sans);font-weight:500;transition:all .12s;display:flex;align-items:center;justify-content:center;gap:5px}}
.card-qr-btn:hover{{border-color:var(--text);color:var(--text);background:var(--gray-bg)}}
.card-qr-btn.disabled{{opacity:.35;pointer-events:none}}

/* MODAL */
#modal{{display:none;position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.45);backdrop-filter:blur(6px);align-items:center;justify-content:center;padding:1rem}}
#modal.open{{display:flex}}
.modal-box{{background:var(--surface);border-radius:var(--r-lg);width:100%;max-width:500px;max-height:92vh;overflow-y:auto;box-shadow:0 24px 64px rgba(0,0,0,.22);animation:modal-in .18s ease}}
@keyframes modal-in{{from{{opacity:0;transform:scale(.97) translateY(8px)}}to{{opacity:1;transform:none}}}}
.modal-hdr{{padding:1.25rem 1.5rem 1rem;display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--surface);z-index:1}}
.modal-serial{{font-family:var(--mono);font-size:15px;font-weight:600;letter-spacing:.5px}}
.modal-pos{{font-size:11px;color:var(--muted);font-family:var(--mono);margin-top:3px}}
.modal-badges{{display:flex;gap:5px;margin-top:6px;flex-wrap:wrap}}
.modal-close{{background:none;border:none;cursor:pointer;color:var(--hint);font-size:18px;line-height:1;padding:.25rem;transition:color .1s;flex-shrink:0}}
.modal-close:hover{{color:var(--text)}}
.modal-body{{padding:1.25rem 1.5rem 1.5rem}}
.modal-device-img{{background:var(--gray-bg);border:1px solid var(--border);border-radius:var(--r-md);padding:.75rem 1rem;display:flex;align-items:center;gap:1rem;margin-bottom:1rem}}
.modal-device-img img{{width:56px;height:56px;object-fit:contain;border-radius:6px}}
.modal-device-img .dev-info .dev-model{{font-size:13px;font-weight:600}}
.modal-device-img .dev-info .dev-serial{{font-family:var(--mono);font-size:11px;color:var(--muted);margin-top:2px}}
.modal-qr-wrap{{background:var(--gray-bg);border:1px solid var(--border);border-radius:var(--r-md);padding:1.25rem;text-align:center;margin-bottom:1.25rem}}
.modal-qr-wrap img{{width:164px;height:164px;border-radius:8px;display:block;margin:0 auto .6rem;image-rendering:pixelated;image-rendering:crisp-edges}}
.modal-qr-wrap p{{font-size:11px;color:var(--muted)}}
.no-qr-wrap{{background:var(--gray-bg);border:1px dashed var(--border);border-radius:var(--r-md);padding:2rem;text-align:center;margin-bottom:1.25rem;font-size:13px;color:var(--hint)}}
.modal-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:1.25rem}}
.mf{{background:var(--gray-bg);border-radius:9px;padding:.75rem}}
.mf-label{{font-size:11px;color:var(--hint);margin-bottom:4px;font-weight:500}}
.mf-val{{font-size:13px;font-weight:600;color:var(--text)}}
.mf-val.mono{{font-family:var(--mono);font-size:12px;word-break:break-all}}
.modal-actions{{display:flex;gap:8px}}
.btn-tms{{flex:1;padding:.65rem;border-radius:var(--r-sm);background:var(--text);color:var(--bg);border:none;font-size:13px;font-weight:600;cursor:pointer;font-family:var(--sans);text-decoration:none;text-align:center;display:block;transition:opacity .15s}}
.btn-tms:hover{{opacity:.8}}
.btn-secondary{{flex:1;padding:.65rem;border-radius:var(--r-sm);background:none;color:var(--text);border:1px solid var(--border);font-size:13px;font-weight:500;cursor:pointer;font-family:var(--sans);text-align:center;transition:background .1s}}
.btn-secondary:hover{{background:var(--gray-bg)}}
.btn-secondary.disabled{{opacity:.35;pointer-events:none}}
.empty{{text-align:center;padding:3rem 1rem;color:var(--muted);font-size:14px;display:none}}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login-screen">
  <div class="login-card">
    <div class="login-brand">
      <div class="logo-mark">
        <svg viewBox="0 0 18 18" fill="none">
          <path d="M3 13V5l6 4 6-4v8" stroke="#F7F7F5" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>
      </div>
      <span class="name">Lokal Money</span>
    </div>
    <p class="login-subtitle">Directorio de Terminales<br>{merchant} · Acceso administrativo</p>
    <label class="field-label">Contraseña</label>
    <div class="pw-wrap">
      <input type="password" id="pw-input" placeholder="••••••••••••" onkeydown="if(event.key==='Enter')doLogin()">
      <button class="eye-btn" onclick="toggleEye(this)">
        <svg viewBox="0 0 20 20" fill="none" width="16" height="16">
          <path d="M1 10s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6z" stroke="currentColor" stroke-width="1.5"/>
          <circle cx="10" cy="10" r="2.5" stroke="currentColor" stroke-width="1.5"/>
        </svg>
      </button>
    </div>
    <div class="login-err" id="login-err">Contraseña incorrecta.</div>
    <button class="btn-primary" onclick="doLogin()">Ingresar →</button>
  </div>
</div>

<!-- APP -->
<div id="app">
  <header>
    <div class="h-brand">
      <div class="logo-mark">
        <svg viewBox="0 0 18 18" fill="none">
          <path d="M3 13V5l6 4 6-4v8" stroke="#F7F7F5" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>
      </div>
      <span class="name">Lokal Money</span>
    </div>
    <div class="h-div"></div>
    <span class="h-title">Terminales · {merchant}</span>
    <div class="h-right">
      <button class="icon-btn" onclick="toggleTheme()" id="theme-btn">🌙 Oscuro</button>
      <button class="icon-btn" onclick="doLogout()">✕ Salir</button>
    </div>
  </header>

  <main>
    <div class="stats-bar" id="stats-bar"></div>
    <div class="toolbar">
      <div class="search-wrap">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="8.5" cy="8.5" r="5.5"/><path d="M15 15l-3-3"/>
        </svg>
        <input type="text" id="search" placeholder="Serial, nombre POS, local, responsable…" oninput="renderCards()">
      </div>
      <select class="filter-select" id="model-sel" onchange="renderCards()">
        <option value="">Todos los modelos</option>
      </select>
      <select class="filter-select" id="app-sel" onchange="renderCards()">
        <option value="">Todas las versiones</option>
      </select>
    </div>
    <div class="chips" id="chips"></div>
    <div class="count-line" id="count-line"></div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty">Sin resultados para esta búsqueda.</div>
  </main>
</div>

<!-- MODAL -->
<div id="modal" onclick="handleModalBg(event)">
  <div class="modal-box">
    <div class="modal-hdr">
      <div>
        <div class="modal-serial" id="m-serial"></div>
        <div class="modal-pos" id="m-pos"></div>
        <div class="modal-badges" id="m-badges"></div>
      </div>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body">
      <div id="m-device-section"></div>
      <div id="m-qr-section"></div>
      <div class="modal-grid">
        <div class="mf"><div class="mf-label">Local asignado</div><div class="mf-val" id="m-local"></div></div>
        <div class="mf"><div class="mf-label">Responsable</div><div class="mf-val" id="m-resp"></div></div>
        <div class="mf"><div class="mf-label">Negocio</div><div class="mf-val" id="m-negocio"></div></div>
        <div class="mf"><div class="mf-label">INT / AMEX</div><div class="mf-val" id="m-intamex"></div></div>
        <div class="mf"><div class="mf-label">Versión App</div><div class="mf-val mono" id="m-app"></div></div>
        <div class="mf"><div class="mf-label">Modelo</div><div class="mf-val" id="m-model"></div></div>
      </div>
      <div class="modal-actions">
        <a id="m-tms" href="#" target="_blank" class="btn-tms">Ver en TMS ↗</a>
        <button class="btn-secondary" id="m-dl-btn" onclick="downloadQR()">⬇ Descargar QR</button>
      </div>
    </div>
  </div>
</div>

<script>
const ACCESS_PASSWORD = {password};
{data_js}

// ── Auth ──────────────────────────────────────────────────────────────────
function doLogin(){{
  if(document.getElementById('pw-input').value===ACCESS_PASSWORD){{
    document.getElementById('login-err').style.display='none';
    document.getElementById('login-screen').style.display='none';
    document.getElementById('app').style.display='block';
    initApp();
  }} else {{
    document.getElementById('login-err').style.display='block';
    document.getElementById('pw-input').select();
  }}
}}
function doLogout(){{
  document.getElementById('app').style.display='none';
  document.getElementById('login-screen').style.display='flex';
  document.getElementById('pw-input').value='';
}}
function toggleEye(btn){{
  const i=document.getElementById('pw-input');
  i.type=i.type==='password'?'text':'password';
  btn.style.opacity=i.type==='text'?'1':'.5';
}}

// ── Theme ─────────────────────────────────────────────────────────────────
let dark=false;
function toggleTheme(){{
  dark=!dark;
  document.documentElement.setAttribute('data-theme',dark?'dark':'');
  document.getElementById('theme-btn').textContent=dark?'☀ Claro':'🌙 Oscuro';
}}

// ── Init: build dynamic filters ───────────────────────────────────────────
function initApp(){{
  buildStats();
  buildModelSelect();
  buildAppSelect();
  buildChips();
  renderCards();
}}

function buildStats(){{
  const total=DATA.length;
  const intamex=DATA.filter(t=>t.int_amex===true).length;
  const byApp={{}};
  DATA.forEach(t=>{{ const a=t.app||'Sin registrar'; byApp[a]=(byApp[a]||0)+1; }});
  let html=pill(total,'terminales');
  if(intamex) html+=pill(intamex,'con INT/AMEX','ok');
  Object.entries(byApp).sort((a,b)=>b[1]-a[1]).forEach(([a,n])=>{{
    const type=a==='Failed'?'err':a==='Por actualizar'?'warn':a==='Sin registrar'?'':'' ;
    html+=pill(n,a||'Sin registrar',type);
  }});
  document.getElementById('stats-bar').innerHTML=html;
}}
function pill(n,label,type=''){{
  const c=type==='ok'?'color:var(--green)':type==='warn'?'color:var(--amber)':type==='err'?'color:var(--red)':'';
  return '<div class="stat-pill"><strong style="'+c+'">'+n+'</strong> '+label+'</div>';
}}

function buildModelSelect(){{
  const models=[...new Set(DATA.map(t=>t.model).filter(Boolean))].sort();
  const sel=document.getElementById('model-sel');
  models.forEach(m=>{{
    const o=document.createElement('option');
    o.value=o.textContent=m; sel.appendChild(o);
  }});
}}
function buildAppSelect(){{
  const apps=[...new Set(DATA.map(t=>t.app||'Sin registrar'))].sort();
  const sel=document.getElementById('app-sel');
  apps.forEach(a=>{{
    const o=document.createElement('option');
    o.value=a; o.textContent=a; sel.appendChild(o);
  }});
}}
function buildChips(){{
  const locals=[...new Set(DATA.map(t=>t.local).filter(Boolean))].sort();
  const container=document.getElementById('chips');
  let html='<div class="chip on" data-local="">Todos</div>';
  locals.forEach(l=>{{ html+=`<div class="chip" data-local="${{esc(l)}}">${{esc(l)}}</div>`; }});
  html+='<div class="chip" data-local="__intamex__">✦ INT/AMEX</div>';
  container.innerHTML=html;
  container.addEventListener('click',e=>{{
    const chip=e.target.closest('.chip');
    if(!chip) return;
    container.querySelectorAll('.chip').forEach(c=>c.classList.remove('on'));
    chip.classList.add('on');
    activeLocal=chip.dataset.local;
    renderCards();
  }});
}}

// ── Render ────────────────────────────────────────────────────────────────
let activeLocal='';

function appClass(app){{
  if(!app||app==='Sin registrar') return 'pill-no';
  if(app==='Failed') return 'pill-err';
  if(app==='Por actualizar') return 'pill-warn';
  return 'pill-ok';
}}
function modelTagClass(model){{
  const m=(model||'').toLowerCase();
  if(m==='n950') return 'tag-n950';
  if(m==='n750') return 'tag-n750';
  return 'tag-n750p';
}}

function renderCards(){{
  const q=document.getElementById('search').value.toLowerCase().trim();
  const modelF=document.getElementById('model-sel').value;
  const appF=document.getElementById('app-sel').value;
  const grid=document.getElementById('grid');
  grid.innerHTML='';
  let shown=0;

  DATA.forEach((t,i)=>{{
    const haystack=(t.serial+' '+t.pos+' '+t.local+' '+(t.resp||'')+' '+t.negocio).toLowerCase();
    if(q && !haystack.includes(q)) return;
    if(modelF && t.model!==modelF) return;
    if(appF && (t.app||'Sin registrar')!==appF) return;
    if(activeLocal==='__intamex__' && t.int_amex!==true) return;
    if(activeLocal && activeLocal!=='__intamex__' && t.local!==activeLocal) return;
    shown++;

    const intPill=t.int_amex===true
      ?'<span class="pill pill-ok">INT/AMEX ✓</span>'
      :'<span class="pill pill-no">Solo nacional</span>';
    const appPill='<span class="pill '+appClass(t.app)+'">'+esc(t.app||'Sin registrar')+'</span>';

    const card=document.createElement('div');
    card.className='card';
    card.onclick=()=>openModal(i);
    card.innerHTML=
      '<div class="card-top">'+
        '<div class="card-badge-row">'+
          '<span class="tag '+modelTagClass(t.model)+'">'+esc(t.model)+'</span>'+
        '</div>'+
        '<div class="card-serial">'+esc(t.serial)+'</div>'+
        '<div class="card-pos">'+esc(t.pos||'—')+'</div>'+
      '</div>'+
      '<div class="card-body">'+
        '<div class="card-local">'+esc(t.local)+'</div>'+
        '<div class="card-resp">'+esc(t.resp||' ')+'</div>'+
        '<div class="card-pills">'+intPill+appPill+'</div>'+
        (t.qr?'<button class="card-qr-btn">📷 Ver QR del POS</button>'
              :'<button class="card-qr-btn disabled">Sin QR registrado</button>')+
      '</div>';
    grid.appendChild(card);
  }});

  document.getElementById('count-line').textContent=
    shown+' terminal'+(shown!==1?'es':'')+' encontrada'+(shown!==1?'s':'');
  document.getElementById('empty').style.display=shown?'none':'block';
}}

function esc(s){{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

// ── Modal ─────────────────────────────────────────────────────────────────
let currentQR='';
function openModal(i){{
  const t=DATA[i];
  document.getElementById('m-serial').textContent=t.serial;
  document.getElementById('m-pos').textContent=t.pos||'Sin POS en Odoo';
  document.getElementById('m-local').textContent=t.local||'—';
  document.getElementById('m-resp').textContent=t.resp||'—';
  document.getElementById('m-negocio').textContent=t.negocio||'—';
  document.getElementById('m-model').textContent=t.model||'—';
  document.getElementById('m-intamex').textContent=
    t.int_amex===true?'✓ Habilitado':t.int_amex===false?'✗ No disponible':'— Sin registrar';
  document.getElementById('m-app').textContent=t.app||'— Sin registrar';

  // Badges
  let b='';
  if(t.int_amex===true) b+='<span class="pill pill-ok">INT/AMEX ✓</span>';
  const ac=appClass(t.app);
  if(t.app) b+='<span class="pill '+ac+'">'+esc(t.app)+'</span>';
  document.getElementById('m-badges').innerHTML=b;

  // Device photo
  const devSec=document.getElementById('m-device-section');
  devSec.innerHTML=t.foto
    ?'<div class="modal-device-img"><img src="'+esc(t.foto)+'" alt="'+esc(t.model)+'" onerror="this.parentElement.style.display=\'none\'"><div class="dev-info"><div class="dev-model">'+esc(t.model)+'</div><div class="dev-serial">'+esc(t.serial)+'</div></div></div>'
    :'';

  // QR
  currentQR=t.qr||'';
  const dlBtn=document.getElementById('m-dl-btn');
  if(t.qr){{
    document.getElementById('m-qr-section').innerHTML=
      '<div class="modal-qr-wrap"><img src="data:image/png;base64,'+t.qr+'" alt="QR POS"><p>Escanear desde la app para abrir el POS en Odoo</p></div>';
    dlBtn.classList.remove('disabled');
  }} else {{
    document.getElementById('m-qr-section').innerHTML=
      '<div class="no-qr-wrap">Sin imagen QR registrada para esta terminal</div>';
    dlBtn.classList.add('disabled');
  }}

  // TMS
  const tmsLink=document.getElementById('m-tms');
  const hasTms=t.tms && t.tms!=='#';
  tmsLink.href=hasTms?t.tms:'#';
  tmsLink.style.opacity=hasTms?'1':'.4';
  tmsLink.style.pointerEvents=hasTms?'':'none';

  document.getElementById('modal').classList.add('open');
  document.body.style.overflow='hidden';
}}
function handleModalBg(e){{
  if(e.target===document.getElementById('modal')) closeModal();
}}
function closeModal(){{
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow='';
}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeModal();}});

function downloadQR(){{
  if(!currentQR) return;
  const a=document.createElement('a');
  a.href='data:image/png;base64,'+currentQR;
  a.download='QR_'+document.getElementById('m-serial').textContent+'.png';
  a.click();
}}
</script>
</body>
</html>
"""


def main():
    args = parse_args()
    rows = load_csv(args.csv)

    merchant = args.merchant or (rows[0].get("negocio", "Merchant") if rows else "Merchant")

    data_js   = build_data_js(rows)
    password  = json.dumps(args.password)

    html = HTML_TEMPLATE.format(
        merchant=merchant,
        password=password,
        data_js=data_js,
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    qr_count = sum(1 for r in rows if os.path.exists(os.path.join(QR_DIR, r.get("serial","") + ".png")))
    print(f"✓ {OUTPUT_FILE} generado")
    print(f"  Merchant : {merchant}")
    print(f"  Terminales: {len(rows)}")
    print(f"  Con QR   : {qr_count}")
    print(f"  Tamaño   : {os.path.getsize(OUTPUT_FILE) // 1024} KB")


if __name__ == "__main__":
    main()
