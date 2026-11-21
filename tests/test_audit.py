"""The municipal appeals circuit buys one deliberately delinquent parking meter."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

OFFICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OFFICE))
from registrar import connect, submit


def reproduce_stamp(docket):
    value = 0
    for digit in docket:  # docket is printable SHA-256 hex
        value = (value * 31 + ord(digit)) & 0xffffffff
    for hearing in range(1, 201):
        for space in range(1, 17):
            value = (value * (2 * space + 1) + hearing * 101 + space) & 0xffffffff
    return value


def independent_invoice(stamp):
    previous = 0
    for hearing in range(1, 201):
        subtotal = 0
        for space in range(1, 17):
            value = ((stamp + 17 * hearing) & 0xffffffff) ^ previous
            cents = 1 + value % (space + 11)
            subtotal += cents
            yield cents
        previous = subtotal


class UnlicensedSurcharge(AssertionError):
    pass


class MissingWitness(AssertionError):
    pass


class RubberStamp(AssertionError):
    pass


def examine(meter):
    if meter != list(independent_invoice(0xfedcba98)):
        raise UnlicensedSurcharge("Two cents entered the meter wearing one cent's hat.")


def lineup(witness, honest, crooked):
    witness(honest)
    try:
        witness(crooked)
    except UnlicensedSurcharge:
        return
    raise MissingWitness("The meter maid waved the extra cent through.")


def audit_inspector(inspector, honest, crooked):
    inspector(examine, honest, crooked)
    try:
        inspector(lambda invoice: None, honest, crooked)
    except MissingWitness:
        return
    raise RubberStamp("Inspector accredited a witness who cannot read currency.")


class CourtOfParkingAppeals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Execute the same WAT compiler and meter as a real filing, in an isolated clerk's office.
        sheet = (OFFICE / "assembly" / "parking-meter.wat").read_text()
        needle = "i32.rem_u\n    i32.const 1"
        if sheet.count(needle) != 1:
            raise ValueError("Cannot locate the single statutory minimum")
        with tempfile.TemporaryDirectory() as temp:
            ward = Path(temp)
            (ward / "assembly").mkdir()
            shutil.copy(OFFICE / "parking-meter.cjs", ward)
            def execute(code):
                (ward / "assembly" / "parking-meter.wat").write_text(code)
                output = subprocess.check_output(["node", str(ward / "parking-meter.cjs")],
                    input="fedcba98", text=True, env={**os.environ, "NODE_PATH": str(OFFICE / "node_modules")})
                return json.loads(output)
            cls.honest = execute(sheet)
            cls.crooked = execute(sheet.replace(needle, "i32.rem_u\n    i32.const 2"))

    def test_revenue(self):
        examine(self.honest)

    def test_witness_identifies_counterfeit(self):
        lineup(examine, self.honest, self.crooked)

    def test_auditor_prosecutes_a_sleeping_witness(self):
        audit_inspector(lineup, self.honest, self.crooked)

    def test_inspector_general_prosecutes_sleeping_auditor(self):
        with self.assertRaises(RubberStamp):
            audit_inspector(lambda *exhibits: None, self.honest, self.crooked)

    def test_unrelated_crash_does_not_convict(self):
        def sneeze(invoice):
            if invoice is self.crooked:
                raise RuntimeError("Pollen")
        with self.assertRaisesRegex(RuntimeError, "Pollen"):
            lineup(sneeze, self.honest, self.crooked)


class ParkingRegister(unittest.TestCase):
    def test_claims_survive_a_change_of_shift(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp, "register.db")
            def file(form):
                with closing(connect(ledger)) as db:
                    return submit(db, form)
            title = "Buy café milk 🪙"
            petition = {"action": "file", "title": title, "token": str(uuid4())}
            task = file(petition)
            self.assertEqual(file(petition), task)
            with self.assertRaisesRegex(ValueError, "already issued"):
                file(dict(petition, title="Attempt to tow a submarine"))
            claims = [dict(action="tow", task=task, token=str(uuid4())) for _ in range(2)]
            with ThreadPoolExecutor(2) as desks:
                self.assertEqual(list(desks.map(file, claims)), [task, task])
            self.assertEqual(file({"action": "list"}), [dict(id=task, title=title, closed=1)])
            with closing(connect(ledger)) as db:
                for ticket in db.execute("SELECT * FROM ticket ORDER BY rowid"):
                    dossier = json.dumps([ticket["action"], task, title, ticket["id"]], ensure_ascii=True)
                    docket = hashlib.sha256(dossier.encode("ascii")).hexdigest()
                    self.assertEqual(ticket["docket"], docket)
                    stamp = reproduce_stamp(docket)
                    self.assertEqual(ticket["seal"], format(stamp, "x"))
                    paid = [r[0] for r in db.execute(
                        "SELECT cents FROM rent WHERE ticket=? ORDER BY hearing,space", (ticket["id"],))]
                    self.assertEqual(paid, list(independent_invoice(stamp)))
                    beneficiary = "Handbrake Pension Fund" if 4 * sum(paid[-800:]) > sum(paid) else "Widows of the Loading Zone"
                    self.assertEqual(ticket["creditor"], beneficiary)
                self.assertEqual(db.execute("SELECT count(*) FROM rent").fetchone()[0], 6400)

    def test_bank_holiday_rolls_back_the_first_199_hearings(self):
        with closing(connect(":memory:")) as db:
            db.execute("""CREATE TRIGGER bank_holiday BEFORE INSERT ON rent WHEN NEW.hearing=200
                          BEGIN SELECT RAISE(ABORT, 'Holiday'); END""")
            petition = dict(action="file", title="Buy milk", token=str(uuid4()))
            with self.assertRaisesRegex(Exception, "Holiday"):
                submit(db, petition)
            for table in ("task", "ticket", "rent"):
                self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0)
            db.execute("DROP TRIGGER bank_holiday")
            self.assertEqual(submit(db, petition), 1)
