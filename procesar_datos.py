"""
procesar_datos.py
─────────────────────────────────────────────────────────────────
Lee TXN_LM_CP.xlsx, filtra por comercio y regenera index.html.

Uso:
    python procesar_datos.py TXN_LM_CP.xlsx "NOMBRE COMERCIO" "UTC-X"
"""

import pandas as pd
import json
import re
import sys
import os

EXCEL_FILE     = "TXN_LM_CP.xlsx"
SHEET_NAME     = "TXN Lokal Money Compago"
OUTPUT_FILE    = "index.html"
TEMPLATE_FILE  = "index.template.html"
DEFAULT_MERCHANT = "HOGAZA HOGAZA"
DEFAULT_TZ_COL   = "UTC-7"

def classify_card(row):
    """Classify card type: Débito or Crédito. AMEX/Internacional added when available."""
    funding = str(row.get("card_funding_source", "")).strip().upper()
    if funding == "DEBIT":
        return "Débito"
    elif funding == "CREDIT":
        return "Crédito"
    else:
        fee = float(row.get("merchant_fee_percentage", 0))
        if fee <= 2.45: return "Débito"
        return "Crédito"

def procesar_excel(path, merchant, tz_col):
    print(f"Leyendo {path}...")
    df = pd.read_excel(path, sheet_name=SHEET_NAME)

    mask = df["merchant_name"].str.strip().str.upper() == merchant.strip().upper()
    df = df[mask].copy()
    if df.empty:
        available = df["merchant_name"].unique().tolist()
        print(f"ERROR: No se encontro el comercio '{merchant}'.")
        print(f"Comercios disponibles: {available}")
        sys.exit(1)
    print(f"OK: {len(df)} filas para '{merchant}'")

    col_name = f"transaction_time ({tz_col})"
    if col_name not in df.columns:
        tz_cols = [c for c in df.columns if c.startswith("transaction_time")]
        print(f"ERROR: No se encontro la columna '{col_name}'.")
        print(f"Columnas disponibles: {tz_cols}")
        sys.exit(1)

    from datetime import timedelta
    # Extract UTC offset hours from tz_col string (e.g. "UTC-7" -> -7)
    import re as _re
    m = _re.search(r"UTC([+-]\d+)", tz_col)
    utc_offset_hours = int(m.group(1)) if m else 0

    df[col_name] = df[col_name].astype(str).str.replace(r"Z+$", "Z", regex=True)
    df["pt_dt"]  = pd.to_datetime(df[col_name], utc=True, errors="coerce")

    # Fallback: rows missing tz column -> compute from transaction_date
    nat_mask = df["pt_dt"].isna()
    if nat_mask.any():
        print(f"AVISO: {nat_mask.sum()} filas sin columna '{col_name}' — calculando desde transaction_date")
        fallback = pd.to_datetime(df.loc[nat_mask, "transaction_date"], utc=True, errors="coerce") \
                   + timedelta(hours=utc_offset_hours)
        df.loc[nat_mask, "pt_dt"] = fallback

    still_nat = df["pt_dt"].isna().sum()
    if still_nat > 0:
        print(f"AVISO: {still_nat} filas sin fecha resoluble — se eliminaran")
        df = df.dropna(subset=["pt_dt"])

    df["date"]       = df["pt_dt"].dt.strftime("%Y-%m-%d")
    df["time"]       = df["pt_dt"].dt.strftime("%H:%M:%S")
    df["hour"]       = df["pt_dt"].dt.hour
    df["dow"]        = df["pt_dt"].dt.day_name()
    df["card_class"] = df.apply(classify_card, axis=1)

    cols = [
        "date", "time", "hour", "dow",
        "transaction_status", "transaction_amount",
        "total_fee_amount", "net_amount_to_merchant",
        "card_type", "issuing_bank",
        "merchant_fee_percentage", "card_class",
        "card_entry_mode", "salesperson_name", "terminal_serial_number",
    ]
    # Only include columns that exist in this file version
    cols = [c for c in cols if c in df.columns]
    records = df[cols].to_dict(orient="records")

    confirmed   = [r for r in records if r["transaction_status"] == "CONFIRMED"]
    total_gross = sum(r["transaction_amount"] for r in confirmed)
    date_from   = min(r["date"] for r in records)
    date_to     = max(r["date"] for r in records)

    print(f"OK: {len(records)} registros | {len(confirmed)} confirmados")
    print(f"OK: Periodo {date_from} a {date_to}")
    print(f"OK: Bruto total ${total_gross:,.2f}")

    return records, date_from, date_to

def regenerar_html(records, date_from, date_to, merchant, password="lokalbi2026"):
    json_data = json.dumps(records, separators=(",", ":"))

    # Use template if available, otherwise use output file
    template_path = TEMPLATE_FILE if os.path.exists(TEMPLATE_FILE) else OUTPUT_FILE
    print(f"Usando plantilla: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Replace merchant name placeholder
    html = html.replace("{{MERCHANT_NAME}}", merchant)
    print(f"OK: Nombre del comercio: {merchant}")

    # 1b. Replace password placeholder
    html = html.replace("{{ACCESS_PASSWORD}}", password)
    print(f"OK: Contrasena configurada")

    # 2. Replace RAW data block
    marker = "let RAW = "
    start  = html.find(marker)
    if start == -1:
        print("ERROR: No se encontro 'let RAW = ' en el HTML.")
        sys.exit(1)

    bracket_open = html.index("[", start)
    depth, pos   = 0, bracket_open
    end = bracket_open
    while pos < len(html):
        if   html[pos] == "[": depth += 1
        elif html[pos] == "]":
            depth -= 1
            if depth == 0:
                end = pos + 1
                break
        pos += 1
    if end < len(html) and html[end] == ";":
        end += 1

    html = html[:start] + "let RAW = " + json_data + html[end:]
    print("OK: Datos embebidos")

    # 3. Update date inputs
    html = re.sub(
        r'<input[^>]*id="dateFrom"[^>]*/>',
        '<input type="date" id="dateFrom" value="' + date_from + '"/>',
        html
    )
    html = re.sub(
        r'<input[^>]*id="dateTo"[^>]*/>',
        '<input type="date" id="dateTo" value="' + date_to + '"/>',
        html
    )
    print("OK: Fechas actualizadas")

    # 4. Remove loadData() from init block if present
    init_pattern = re.compile(
        r'(scheduleRefresh\(\);)\s*(?://[^\n]*)?\s*loadData\(\);',
        re.MULTILINE
    )
    html, n = init_pattern.subn(r'\1', html)
    if n:
        print(f"OK: loadData() eliminado del init ({n} vez/veces)")

    # 5. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    months_es = ["Ene","Feb","Mar","Abr","May","Jun",
                 "Jul","Ago","Sep","Oct","Nov","Dic"]
    def fmt(d):
        y, m, day = d.split("-")
        return f"{int(day)} {months_es[int(m)-1]} {y}"

    print(f"LISTO: {OUTPUT_FILE} generado ({size_kb:.1f} KB)")
    print(f"LISTO: Periodo {fmt(date_from)} — {fmt(date_to)}")

if __name__ == "__main__":
    excel_path = sys.argv[1] if len(sys.argv) > 1 else EXCEL_FILE
    merchant   = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MERCHANT
    tz_col     = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_TZ_COL
    password   = sys.argv[4] if len(sys.argv) > 4 else "lokalbi2026"

    if not os.path.exists(excel_path):
        print(f"ERROR: No se encontro el archivo {excel_path}")
        sys.exit(1)

    print(f"Comercio: {merchant} | Huso horario: {tz_col}")
    records, date_from, date_to = procesar_excel(excel_path, merchant, tz_col)
    regenerar_html(records, date_from, date_to, merchant, password)
