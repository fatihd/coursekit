import sqlite3, json, time, os

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS source(id TEXT PRIMARY KEY, role TEXT, name TEXT, fmt TEXT,
  page_offset INTEGER, url_template TEXT, images_dir TEXT);
CREATE TABLE IF NOT EXISTS page(source TEXT, scan INTEGER, printed INTEGER, lines TEXT,
  PRIMARY KEY(source, scan));
CREATE TABLE IF NOT EXISTS block(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, label TEXT,
  section TEXT, section_basis TEXT, instruction TEXT, start_scan INT, start_line INT,
  end_scan INT, end_line INT, status TEXT DEFAULT 'candidate', origin TEXT DEFAULT 'auto',
  note TEXT DEFAULT '', key_ref TEXT DEFAULT '', created REAL, updated REAL);
CREATE TABLE IF NOT EXISTS item(id INTEGER PRIMARY KEY AUTOINCREMENT, block_id INT, ord INT,
  part TEXT, num TEXT, prompt_ocr TEXT, prompt TEXT, answer_ocr TEXT, answer TEXT, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS keyseg(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, section TEXT,
  part TEXT, pair INT, start_scan INT, start_line INT, end_scan INT, end_line INT);
CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, block_id INT,
  item_id INT, field TEXT, old TEXT, new TEXT);
CREATE TABLE IF NOT EXISTS ocr(source TEXT, scan INT, line INT, engine TEXT, lang TEXT, text TEXT, conf REAL, ts REAL,
  PRIMARY KEY(source, scan, line, engine));
CREATE TABLE IF NOT EXISTS curated(okey TEXT PRIMARY KEY, items TEXT, author TEXT, note TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS item_block ON item(block_id, ord);
"""

def connect(project):
    os.makedirs(project, exist_ok=True)
    con = sqlite3.connect(os.path.join(project, "exwb.db"), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    for table, col, typ in (("page", "w", "INTEGER"), ("page", "h", "INTEGER"), ("source", "pdf", "TEXT"), ("source", "pdf_delta", "INTEGER"), ("ocr", "box", "TEXT"), ("item", "hint", "TEXT"), ("item", "explain", "TEXT"), ("item", "data", "TEXT")):
        if col not in [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    con.commit()
    return con

def get_meta(con, k, default=None):
    r = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else default

def set_meta(con, k, v):
    con.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, json.dumps(v)))
    con.commit()

def now():
    return time.time()
