import argparse, json, sys
from .db import connect
from . import core, script, server
from .db import get_meta

def main():
    ap = argparse.ArgumentParser(prog="exwb", description="Exercise workbench")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="ingest OCR sources and generate candidate blocks (safe to re-run; keeps your work)")
    b.add_argument("profile"); b.add_argument("project")
    s = sub.add_parser("serve", help="open the review UI"); s.add_argument("project"); s.add_argument("--port", type=int, default=8765)
    e = sub.add_parser("export", help="write JSON"); e.add_argument("project"); e.add_argument("-o", default="-"); e.add_argument("--all", action="store_true", help="include unfinished blocks")
    r = sub.add_parser("reset", help="discard review work: blocks back to fresh candidates (backs up exwb.db first)")
    r.add_argument("project"); r.add_argument("--block", type=int, nargs="*", help="only these block ids")
    o = sub.add_parser("ocr", help="local tesseract OCR of block lines (language per line), cached; re-derives untouched candidates")
    o.add_argument("project"); o.add_argument("--block", type=int, nargs="*", help="only these block ids (default: all)")
    o.add_argument("--force", nargs="?", const=True, default=False, help="re-OCR lines already cached ('--force he' = Hebrew lines only)")
    c = sub.add_parser("curate", help="import curated items: JSON {block_id, author?, items:[{part,num,prompt,answer,note?}]} (or a list of such)")
    c.add_argument("project"); c.add_argument("file")
    g = sub.add_parser("ignore", help="drop blocks for good (kept across build/reset); e.g. ignore proj 1 --reason '§1 transliteration'")
    g.add_argument("project"); g.add_argument("block", type=int, nargs="+"); g.add_argument("--reason", default="not an exercise")
    h = sub.add_parser("hold", help="keep blocks but leave them out of export (kept across build/reset); --release to undo")
    h.add_argument("project"); h.add_argument("block", type=int, nargs="+"); h.add_argument("--reason", default="held")
    h.add_argument("--release", action="store_true")
    a = ap.parse_args()
    con = connect(a.project)
    if a.cmd != "build": script.apply(get_meta(con, "profile") or {})
    if a.cmd == "build": core.build(con, a.profile)
    elif a.cmd == "serve": server.serve(con, a.project, a.port)
    elif a.cmd == "reset":
        import os, shutil, time
        bak = os.path.join(a.project, time.strftime("exwb-%Y%m%d-%H%M%S.db.bak"))
        con.commit(); shutil.copy2(os.path.join(a.project, "exwb.db"), bak)
        print(f"backup: {bak}\nreset {core.reset(con, set(a.block or []))} blocks")
    elif a.cmd == "ocr":
        from . import ocr
        st = ocr.available(("grc", "eng") if script.ACTIVE["name"] == "greek" else ("heb", "eng"))
        if not st["ok"]: sys.exit("local OCR unavailable: " + st["why"])
        ids = a.block or [r["id"] for r in con.execute("SELECT id FROM block WHERE status!='skipped' ORDER BY start_scan")]
        for bid in ids: ocr.ocr_block(con, bid, a.project, force=a.force)
        for (ks,) in con.execute("SELECT id FROM source WHERE role='key'").fetchall(): core.rebuild_keysegs(con, ks)
        for bid in ids:
            b = con.execute("SELECT status FROM block WHERE id=?", (bid,)).fetchone()
            if b["status"] == "candidate" and core.untouched(con, bid, items_only=True):
                core.regenerate(con, bid, log=False)
        print("done; in-progress/done blocks keep their items (use Re-detect items in the UI to apply OCR text there)")
    elif a.cmd == "hold":
        for bid in a.block: core.set_hold(con, bid, "" if a.release else a.reason); print(bid, "released" if a.release else "held")
    elif a.cmd == "ignore":
        for bid in a.block: print(bid, core.delete_block(con, bid, a.reason))
    elif a.cmd == "curate":
        data = json.load(open(a.file, encoding="utf8"))
        for d in (data if isinstance(data, list) else [data]):
            core.curate(con, int(d["block_id"]), d["items"], d.get("author", ""), d.get("note", ""))
            print(f"block {d['block_id']}: {len(d['items'])} curated items")
    elif a.cmd == "export":
        data = json.dumps(core.export(con, "all" if a.all else "done"), ensure_ascii=False, indent=1)
        (sys.stdout.write(data) if a.o == "-" else open(a.o, "w", encoding="utf8").write(data))
main()
