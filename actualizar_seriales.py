#!/usr/bin/env python3
"""
actualizar_seriales.py
Lee el spreadsheet de terminales de Baja Alliance desde Google Sheets API
y actualiza la lista blanca de seriales en turno.html.
"""

import json, re, os, sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ── CONFIG ──────────────────────────────────────────────────────────────────
SPREADSHEET_ID = '1pGxvTKanguPsOG8qy0RBHcv2t9TB9Z3COa8XEVjsNRk'
SHEET_RANGE    = 'Data Base!A:A'   # Solo la columna SERIAL
HTML_FILE      = 'turno.html'
# ────────────────────────────────────────────────────────────────────────────

def get_serials():
    creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
    if not creds_json:
        raise ValueError("Falta variable de entorno GOOGLE_SHEETS_CREDENTIALS")

    creds_data = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_data,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=SHEET_RANGE
    ).execute()

    rows = result.get('values', [])
    serials = []
    for row in rows:
        if not row:
            continue
        val = row[0].strip()
        # Skip header and empty rows
        if val.upper() == 'SERIAL' or not val:
            continue
        # Only include rows that look like terminal serials (alphanumeric)
        if re.match(r'^[A-Z0-9]+$', val):
            serials.append(val)

    return serials

def serials_to_last5(serials):
    last5_set = set()
    for s in serials:
        num = re.sub(r'^[A-Z]+', '', s)
        last5 = num[-5:] if len(num) >= 5 else num
        if last5:
            last5_set.add(last5)
    return sorted(last5_set)

def update_html(last5_list):
    with open(HTML_FILE, 'r') as f:
        lines = f.readlines()

    js_set = "new Set([" + ", ".join(f"'{x}'" for x in last5_list) + "])"
    new_line = f"  const VALID_SERIALS = {js_set};\n"

    found = False
    new_lines = []
    for line in lines:
        if 'const VALID_SERIALS' in line and 'new Set' in line:
            new_lines.append(new_line)
            found = True
        else:
            new_lines.append(line)

    if not found:
        print("⚠️  No se encontró VALID_SERIALS en turno.html — verifica el archivo")
        sys.exit(1)

    with open(HTML_FILE, 'w') as f:
        f.writelines(new_lines)

    print(f"✅ Lista blanca actualizada: {len(last5_list)} seriales")

if __name__ == '__main__':
    print("Leyendo seriales desde Google Sheets...")
    serials = get_serials()
    print(f"  {len(serials)} seriales encontrados en el sheet")

    last5 = serials_to_last5(serials)
    print(f"  {len(last5)} sufijos únicos de 5 dígitos")

    update_html(last5)
