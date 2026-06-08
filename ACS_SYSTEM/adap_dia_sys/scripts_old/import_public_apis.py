#!/usr/bin/env python3
# import_public_apis.py
# Parse ~/public-apis/README.md and export CSV + SQLite registry
# Put this into ~/adaptive_vault/scripts/

import os
import re
import csv
import sqlite3
from pathlib import Path

HOME = Path.home()
SRC = HOME / "public-apis" / "README.md"
OUT_DIR = Path.home() / "adaptive_public_apis"
CSV_PATH = OUT_DIR / "public_apis.csv"
DB_PATH = OUT_DIR / "public_apis.db"

# Markdown table row pattern: | API | Description | Auth | HTTPS | CORS | Link |
# We'll be permissive and split cells by pipe, trimming spaces.
def parse_md_table(md_lines):
    entries = []
    header_seen = False
    # simple state machine: when a header row is seen then rows follow until blank or next header
    for line in md_lines:
        if line.strip().startswith("|") and re.search(r"\|\s*Description\s*\|", line, re.IGNORECASE):
            header_seen = True
            continue
        if not header_seen:
            continue
        if line.strip().startswith("|---"):
            # table separator
            continue
        if line.strip().startswith("|") and "|" in line:
            # split into columns
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            # ignore short/malformed lines
            if len(cols) < 6:
                continue
            name = cols[0]
            description = cols[1]
            auth = cols[2]
            https = cols[3]
            cors = cols[4]
            link = cols[5]
            entries.append({
                "name": name,
                "description": description,
                "auth": auth,
                "https": https,
                "cors": cors,
                "link": link
            })
        else:
            # non-table line ends the table
            break
    return entries

def extract_all_tables(md_text):
    # The public-apis README is organized with headings and a table beneath each heading.
    # We'll find each table by looking at '### Category' then the following lines.
    lines = md_text.splitlines()
    all_entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # capture category headings (e.g., "### Animals")
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            category = m.group(1).strip()
            # collect lines for the table immediately after heading
            j = i + 1
            table_lines = []
            # gather up to next heading or until we leave the table zone
            while j < len(lines):
                if re.match(r"^###\s+(.+)$", lines[j]) or re.match(r"^##\s+(.+)$", lines[j]):
                    break
                table_lines.append(lines[j])
                j += 1
            # parse this chunk for table entries
            rows = parse_md_table(table_lines)
            for r in rows:
                r["category"] = category
            all_entries.extend(rows)
            i = j
        else:
            i += 1
    return all_entries

def write_csv(entries, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = ["name","category","description","auth","https","cors","link"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for e in entries:
            writer.writerow({k: e.get(k,"") for k in keys})
    print(f"[OK] CSV written: {path}")

def write_sqlite(entries, dbpath):
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dbpath))
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS apis (
        id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        description TEXT,
        auth TEXT,
        https TEXT,
        cors TEXT,
        link TEXT
    )""")
    cur.execute("DELETE FROM apis")  # replace existing content to avoid duplicates
    ins = "INSERT INTO apis (name,category,description,auth,https,cors,link) VALUES (?,?,?,?,?,?,?)"
    rows = [(e["name"], e["category"], e["description"], e["auth"], e["https"], e["cors"], e["link"]) for e in entries]
    cur.executemany(ins, rows)
    conn.commit()
    conn.close()
    print(f"[OK] SQLite DB written: {dbpath} ({len(rows)} rows)")

def dedupe_entries(entries):
    seen = set()
    out = []
    for e in entries:
        key = (e["name"].lower().strip(), e["link"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out

def main():
    if not SRC.exists():
        print("[ERR] source README not found:", SRC)
        return
    md_text = SRC.read_text(encoding="utf-8", errors="ignore")
    entries = extract_all_tables(md_text)
    print(f"[INFO] parsed {len(entries)} raw entries from README")
    entries = dedupe_entries(entries)
    print(f"[INFO] {len(entries)} after dedup")
    write_csv(entries, CSV_PATH)
    write_sqlite(entries, DB_PATH)
    print("[DONE] exported CSV & DB to", OUT_DIR)

if __name__ == "__main__":
    main()
