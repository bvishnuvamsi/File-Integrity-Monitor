import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pathlib import Path
from fimlite import db as dbmod

def main():
    db_path = Path("data/fimlite.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = dbmod.connect(db_path)
    dbmod.init_db(con)

    baseline = {
        "foo.txt": {"size": 10, "sha256": "abc", "mtime": 123.0},
        "bar.py":  {"size": 20, "sha256": "def", "mtime": 456.0},
    }
    dbmod.write_baseline(con, baseline)
    print("Baseline count:", len(dbmod.read_baseline(con)))

    sid = dbmod.start_scan(con)
    dbmod.log_change(con, sid, "foo.txt", "modified", "abc", "zzz", "medium", None)
    dbmod.end_scan(con, sid)

    for row in con.execute("SELECT scan_id, started_at, ended_at FROM scans"):
        print("scan:", dict(row))
    for row in con.execute("SELECT path, change_type, severity FROM changes"):
        print("change:", dict(row))

if __name__ == "__main__":
    main()
