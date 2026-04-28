"""
fetch_compago.py
─────────────────────────────────────────────────────────────────
Descarga transacciones desde la API de Compago y genera index.html.

Uso:
    python fetch_compago.py "<MERCHANT_NAME>" "UTC-X" "<PASSWORD>" [days_back]
    python fetch_compago.py "ALL" "UTC-6" "<PASSWORD>" [days_back]  # Holding

Variables de entorno:
    COMPAGO_API_KEY : API key de Compago (requerida)
"""

import os, sys, json, re, urllib.request, urllib.parse, time
from datetime import datetime, timedelta, timezone

# ── CONFIG ────────────────────────────────────────────────────────
BASE_URL   = "https://api.honor.compago.com/api/developer/payment"
PAGE_SIZE  = 100
OUTPUT_FILE   = "index.html"
TEMPLATE_FILE = "index.template.html"

# Organization ID map (merchant name → Compago org UUID)
ORG_IDS = {
    "Alvaro Bazán Estrada":               "daecdc56-7642-44d6-bd81-4217911eb098",
    "TORO ALIMENTOS":                     "82dd8ac0-8bf8-4c2e-8dce-f2c407c0410d",
    "CON ACENTO":                         "6f392919-b91f-4ab8-b43b-40687ca2a6f0",
    "Concierge":                          "abe74e1f-3753-41b5-886a-15b47405462c",
    "COORDINADOS":                        "802785dc-48ac-4ae3-92a7-baf32e59ae3a",
    "CRUZ ROJA MEXICANA":                 "34211e1d-c39a-4827-ad9e-e3cd0ddb1953",
    "HOGAZA HOGAZA":                      "17ee7656-7c47-49d7-b156-7c43bd05a146",
    "Lokal Money":                        "0608b34a-abe3-4957-8df0-e5e18ef6de55",
    "Lokal Pool":                         None,  # not seen in API yet
    "LokalMoney":                         "e8ce56ce-6fa4-482c-846e-276a1a620693",
    "Mariela Alonso Ablanedo":            "5080e8fd-6ea2-4771-8c88-46fedff8d4b3",
    "MIPTECH":                            "ebd2e033-c99e-44fa-8fcc-0111e600dc7b",
    "Odoo":                               "e3ae8983-d549-47e7-b6ca-d05707e186a4",
    "Petlicious":                         "8c3b7cab-0e31-413c-a09c-8f28645b08f9",
    "PRONOIA":                            "98c1b82f-b799-44e5-8788-e89ff2ad34a5",
    "PSF Shipping":                       None,
    "RAMALHOS HORNOS MEXICO":             None,
    "Seguro Mar":                         "3d7ff343-918e-41ba-b038-954bfbf8b334",
    "START BUSINESS BUILDER AND CONSULTING": None,
    "TI AMBIENTAL":                       "b9679fe3-e449-480d-9896-a72e00669671",
    "TREVI\u00d1O TI":                   "74f38cd9-44f1-4e76-ae9a-b041d4a8a5dd",
    "YAAKUNAJ":                           None,
}

# ── ARGS ──────────────────────────────────────────────────────────
merchant  = sys.argv[1] if len(sys.argv) > 1 else "HOGAZA HOGAZA"
tz_col    = sys.argv[2] if len(sys.argv) > 2 else "UTC-6"
password  = sys.argv[3] if len(sys.argv) > 3 else "lokalbi2026"
days_back = int(sys.argv[4]) if len(sys.argv) > 4 else 365
is_holding = merchant.upper() == "ALL"

api_key = os.environ.get("COMPAGO_API_KEY", "")
if not api_key:
    print("ERROR: COMPAGO_API_KEY no configurada")
    sys.exit(1)

# ── TIMEZONE ──────────────────────────────────────────────────────
m = re.search(r"UTC([+-]\d+)", tz_col)
utc_offset_hours = int(m.group(1)) if m else -6
tz_delta = timedelta(hours=utc_offset_hours)

# ── DATE RANGE ────────────────────────────────────────────────────
now_local = datetime.now(timezone.utc) + tz_delta
# Compago API tiene un desfase de +1 día en el filtro de fechas
# Para obtener datos del día X hay que pedir el día X+1
date_to   = (now_local + timedelta(days=1)).strftime("%Y-%m-%d")
date_from = (now_local - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")

print(f"Modo: {'HOLDING (todos los comercios)' if is_holding else merchant}")
print(f"Período: {date_from} → {date_to} | Zona: {tz_col}")

# ── FETCH ─────────────────────────────────────────────────────────
def fetch_page(params):
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == 4: raise
            wait = (attempt + 1) * 5
            print(f"  Reintento {attempt+1}/4 en {wait}s ({e})")
            time.sleep(wait)

def fetch_all(org_id=None):
    records = []
    offset  = 0
    while True:
        params = {
            "limit": PAGE_SIZE,
            "offset": offset,
            "createdAtFrom": date_from,
            "createdAtTo":   date_to,
        }
        if org_id:
            params["organizationId"] = org_id
        d     = fetch_page(params)
        batch = d.get("data", [])
        records.extend(batch)
        count = d["pagination"]["count"]
        print(f"  {len(records)} registros...")
        if count < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return records

# ── DOWNLOAD ──────────────────────────────────────────────────────
if is_holding:
    # Download all at once (no org filter)
    raw_data = fetch_all()
else:
    org_id = ORG_IDS.get(merchant)
    if org_id:
        print(f"Usando organizationId: {org_id}")
        raw_data = fetch_all(org_id)
    else:
        # Fallback: download all and filter locally
        print("AVISO: org ID no encontrado, descargando todo y filtrando localmente")
        raw_data = fetch_all()

print(f"Total descargado: {len(raw_data)} registros")

# ── CARD CLASSIFICATION ───────────────────────────────────────────
def classify_card(funding, network, fee):
    f = (funding or "").upper()
    n = (network or "").upper()
    if f == "DEBIT":   return "Débito"
    elif f == "CREDIT":
        if n == "AMEX":    return "AMEX"
        if n == "UNKNOWN": return "Crédito Internacional"
        return "Crédito"
    else:
        fee = float(fee or 0)
        if fee <= 2.45: return "Débito"
        if fee <= 2.84: return "Crédito"
        if fee <= 2.99: return "Crédito Plus"
        return "Crédito Internacional"

# ── TRANSFORM ─────────────────────────────────────────────────────
def transform(raw):
    records = []
    for r in raw:
        org_name = (r.get("organization") or {}).get("name", "")
        if not is_holding and org_name.strip().upper() != merchant.strip().upper():
            continue

        created_utc = r.get("createdAt") or ""
        try:
            dt_utc   = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
            dt_local = dt_utc + tz_delta
        except Exception:
            continue

        card = r.get("cardInformation") or {}
        disb = r.get("paymentDisbursement") or {}
        term = r.get("terminal") or {}
        funding = card.get("fundingSource", "")
        network = card.get("networkType", "")
        fee_pct = disb.get("finalFeePercentageForMerchant", 0)

        salesperson = r.get("salesperson") or {}
        branch      = r.get("businessStoreBranch") or {}
        rec = {
            "date":                    dt_local.strftime("%Y-%m-%d"),
            "time":                    dt_local.strftime("%H:%M:%S"),
            "hour":                    dt_local.hour,
            "dow":                     dt_local.strftime("%A"),
            "transaction_status":      r.get("status", ""),
            "transaction_amount":      float(r.get("amount", 0)),
            "total_fee_amount":        float(disb.get("feeAmount", 0)) + float(disb.get("merchantIvaFeeAmount", 0)),
            "net_amount_to_merchant":  float(disb.get("merchantTakeAmount", 0)),
            "card_type":               network,
            "issuing_bank":            card.get("issuingBank", "") or "",
            "merchant_fee_percentage": float(fee_pct),
            "card_class":              classify_card(funding, network, fee_pct),
            "card_entry_mode":         card.get("entryMode", "") or "",
            "terminal_serial_number":  term.get("serialNumber", "") or "",
            "salesperson_username":          salesperson.get("username", "") or "",
            "salesperson_name":              salesperson.get("name", "") or "",
            "business_store_branch_name":    branch.get("name", "") or "",
        }
        if is_holding:
            rec["merchant"] = org_name.strip()
        records.append(rec)
    return records

records = transform(raw_data)
print(f"Registros procesados: {len(records)}")

if not records:
    print(f"ERROR: No hay registros para '{merchant}' en el período")
    sys.exit(1)

confirmed    = [r for r in records if r["transaction_status"] == "CONFIRMED"]
date_from_d  = min(r["date"] for r in records)
date_to_d    = max(r["date"] for r in records)
total_gross  = sum(r["transaction_amount"] for r in confirmed)

print(f"Confirmadas: {len(confirmed)} | Bruto: ${total_gross:,.2f}")
print(f"Período real: {date_from_d} → {date_to_d}")

# ── INJECT INTO TEMPLATE ──────────────────────────────────────────
template_path = TEMPLATE_FILE if os.path.exists(TEMPLATE_FILE) else OUTPUT_FILE
with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

json_data    = json.dumps(records, separators=(",", ":"))
display_name = "LOKAL MONEY HOLDING" if is_holding else merchant

html = html.replace("{{MERCHANT_NAME}}", display_name)
html = html.replace("{{ACCESS_PASSWORD}}", password)

# Replace RAW block
start   = html.find("let RAW = ")
bracket = html.index("[", start)
depth, pos = 0, bracket
while pos < len(html):
    if html[pos] == "[": depth += 1
    elif html[pos] == "]":
        depth -= 1
        if depth == 0:
            end = pos + 1; break
    pos += 1
if html[end] == ";": end += 1
html = html[:start] + "let RAW = " + json_data + html[end:]

# Date inputs
html = re.sub(r'<input[^>]*id="dateFrom"[^>]*/>', f'<input type="date" id="dateFrom" value="{date_from_d}"/>', html)
html = re.sub(r'<input[^>]*id="dateTo"[^>]*/>', f'<input type="date" id="dateTo" value="{date_to_d}"/>', html)

# Remove loadData
html, _ = re.compile(r'(scheduleRefresh\(\);)\s*(?://[^\n]*)?\s*loadData\(\);', re.MULTILINE).subn(r'\1', html)

# Holding: inject merchant breakdown
if is_holding and '// ── FEE TABLE' in html:
    MERCHANT_JS = '''
  // ── MERCHANT BREAKDOWN ─────────────────────────────────────
  const merchantMap = {};
  confirmed.forEach(r => {
    const m = (r.merchant || 'OTROS').trim();
    if (!merchantMap[m]) merchantMap[m] = {count:0, gross:0};
    merchantMap[m].count++;
    merchantMap[m].gross += r.transaction_amount;
  });
  const merchants = Object.entries(merchantMap).sort((a,b) => b[1].gross - a[1].gross);
  const maxMerchant = merchants[0]?.[1].gross || 1;
  const mColors = ['#00c2a8','#3b82f6','#f5a623','#a78bfa','#e85d5d','#06b6d4','#84cc16','#f97316','#ec4899','#8b5cf6','#14b8a6','#eab308','#ef4444','#6366f1','#10b981'];
  const merchantBarsEl = document.getElementById('merchantBars');
  if (merchantBarsEl) {
    const totalMG = merchants.reduce((s,[,v]) => s + v.gross, 0);
    let cum = 0; const pareto = [];
    for (const [n,v] of merchants) { pareto.push([n,v]); cum+=v.gross; if(cum/totalMG>=0.80) break; }
    const othersG = totalMG - pareto.reduce((s,[,v])=>s+v.gross,0);
    merchantBarsEl.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;padding-bottom:10px;border-bottom:1px solid var(--border);">
      <span style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.7px;color:var(--muted);">Total consolidado</span>
      <span style="font-family:'Barlow',sans-serif;font-size:20px;font-weight:800;color:var(--teal);">${fmt(totalMG)}</span>
    </div><div style="font-size:10.5px;color:var(--muted);margin-bottom:10px;">Top ${pareto.length} comercio${pareto.length>1?'s':''} representan el 80% del volumen</div>`
    + pareto.map(([n,v],i)=>`<div class="bank-row"><div class="bank-name" style="width:140px;font-size:11px;">${n}</div><div class="bank-bar-wrap"><div class="bank-bar-fill" style="width:${(v.gross/maxMerchant*100).toFixed(1)}%;background:${mColors[i%mColors.length]};"></div></div><div class="bank-amount">${fmt(v.gross)}</div></div>`).join('')
    + (othersG>0?`<div class="bank-row" style="opacity:0.6;"><div class="bank-name" style="width:140px;font-size:11px;font-style:italic;">Otros</div><div class="bank-bar-wrap"><div class="bank-bar-fill" style="width:${(othersG/maxMerchant*100).toFixed(1)}%;background:rgba(120,130,150,0.5);"></div></div><div class="bank-amount">${fmt(othersG)}</div></div>`:'');
  }
  destroyChart('merchantChart');
  if (document.getElementById('merchantChart')) {
    const total = merchants.reduce((s,[,v])=>s+v.gross,0);
    let cumC=0; const pC=[];
    for(const [n,v] of merchants){pC.push([n,v]);cumC+=v.gross;if(cumC/total>=0.80)break;}
    const oC=total-cumC;
    const lbl=pC.map(([n])=>n); const dat=pC.map(([,v])=>v.gross); const col=pC.map((_,i)=>mColors[i%mColors.length]);
    if(oC>0){lbl.push('Otros');dat.push(oC);col.push('rgba(120,130,150,0.4)');}
    charts.merchantChart=new Chart(document.getElementById('merchantChart'),{type:'doughnut',
      data:{labels:lbl,datasets:[{data:dat,backgroundColor:col,borderWidth:0,hoverOffset:6}]},
      options:{responsive:true,maintainAspectRatio:false,cutout:'55%',
        plugins:{legend:{display:true,position:'right',labels:{boxWidth:10,font:{size:10},padding:8}},
          tooltip:{callbacks:{label:ctx=>{const t=ctx.dataset.data.reduce((a,b)=>a+b,0);return' '+ctx.label+': '+fmt(ctx.raw)+' ('+(ctx.raw/t*100).toFixed(1)+'%)';}}}},
        animation:{onComplete:function(){const chart=this;const ctx2=chart.ctx;
          const t=chart.data.datasets[0].data.reduce((a,b)=>a+b,0);
          chart.data.datasets[0].data.forEach((val,i)=>{const pct=val/t*100;if(pct<4)return;
            const meta=chart.getDatasetMeta(0);const arc=meta.data[i];
            const mid=arc.startAngle+(arc.endAngle-arc.startAngle)/2;
            const r2=(arc.outerRadius+arc.innerRadius)/2;
            const x=arc.x+Math.cos(mid)*r2;const y=arc.y+Math.sin(mid)*r2;
            ctx2.save();ctx2.fillStyle='#fff';ctx2.font='bold 11px Barlow,sans-serif';
            ctx2.textAlign='center';ctx2.textBaseline='middle';
            ctx2.fillText(pct.toFixed(1)+'%',x,y);ctx2.restore();});}}
      }});
  }
'''
    html = html.replace('  // ── FEE TABLE', MERCHANT_JS + '  // ── FEE TABLE')

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

months_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
def fmt_d(d):
    y,mo,day=d.split("-")
    return f"{int(day)} {months_es[int(mo)-1]} {y}"

print(f"LISTO: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)/1024:.1f} KB)")
print(f"LISTO: {fmt_d(date_from_d)} — {fmt_d(date_to_d)}")
