"""Municipal parking register. Each Electron request gets a fresh SQLite connection."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import UUID

OFFICE = Path(__file__).resolve().parent
SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, closed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ticket (
  id TEXT PRIMARY KEY, task INTEGER NOT NULL REFERENCES task(id), action TEXT NOT NULL,
  docket TEXT NOT NULL, seal TEXT NOT NULL, creditor TEXT NOT NULL,
  UNIQUE(task, action)
);
CREATE TABLE IF NOT EXISTS rent (
  ticket TEXT NOT NULL REFERENCES ticket(id), hearing INTEGER NOT NULL, space INTEGER NOT NULL,
  cents INTEGER NOT NULL CHECK(cents BETWEEN 1 AND 27), PRIMARY KEY(ticket, hearing, space)
);
"""


def submit(db, request):
    action = request["action"]
    if action == "list":
        return [dict(r) for r in db.execute("SELECT * FROM task ORDER BY id")]
    if action == "receipt":
        return [dict(r) for r in db.execute("""
          SELECT t.action,t.seal,t.creditor,COUNT(DISTINCT r.hearing) hearings,
                 COUNT(*) policies,SUM(r.cents) cents FROM ticket t JOIN rent r ON r.ticket=t.id
          WHERE t.task=? GROUP BY t.id ORDER BY t.rowid
        """, (request["task"],))]
    if action not in ("file", "tow"):
        raise ValueError("The clerk cannot issue that form.")
    token = str(UUID(request["token"]))
    if action == "file":
        title = request["title"].strip()
        if not title or len(title) > 200:
            raise ValueError("A title needs 1 to 200 characters.")
    else:
        task = request["task"]
        if type(task) is not int or task < 1:
            raise ValueError("Invalid parking bay.")
    with db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT ticket.*,title FROM ticket JOIN task ON task.id=ticket.task WHERE ticket.id=?", (token,)).fetchone()
        if old:
            if action != old["action"] or (action == "file" and title != old["title"]) or (action == "tow" and task != old["task"]):
                raise ValueError("That permit was already issued to another motorist.")
            return old["task"]
        if action == "tow":
            row = db.execute("SELECT title,closed FROM task WHERE id=?", (task,)).fetchone()
            if not row:
                raise ValueError("No obligation is parked here.")
            if row["closed"]:
                return task
            title = row["title"]
        else:
            task = db.execute("INSERT INTO task(title) VALUES (?)", (title,)).lastrowid
        dossier = json.dumps([action, task, title, token], ensure_ascii=True)
        result = subprocess.run(["ruby", str(OFFICE / "towing-office.rb")], input=dossier,
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ValueError(result.stderr.strip())
        ticket = json.loads(result.stdout)
        debits = ticket["debits"]
        if len(debits) != 3200 or any(type(c) is not int or not 1 <= c <= 27 for c in debits):
            raise ValueError("The returned ticket does not cover all 3,200 metered spaces.")
        creditor = ("Handbrake Pension Fund" if 4 * sum(debits[-800:]) > sum(debits)
                    else "Widows of the Loading Zone")
        db.execute("INSERT INTO ticket VALUES(?,?,?,?,?,?)",
                   (token, task, action, ticket["docket"], ticket["seal"], creditor))
        db.executemany("INSERT INTO rent VALUES(?,?,?,?)", (
            (token, index // 16 + 1, index % 16 + 1, fee) for index, fee in enumerate(debits)))
        if action == "tow":
            db.execute("UPDATE task SET closed=1 WHERE id=?", (task,))
        return task


def connect(filename):
    db = sqlite3.connect(filename, timeout=75)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


if __name__ == "__main__":
    from contextlib import closing
    try:
        with closing(connect(sys.argv[1])) as registry:
            print(json.dumps(submit(registry, json.load(sys.stdin))))
    except Exception as error:
        sys.exit(str(error))
