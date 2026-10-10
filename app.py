from datetime import datetime

import psycopg2
from psycopg2 import errors
from flask import Flask, request, jsonify
from werkzeug.exceptions import HTTPException

from db import get_connection

app = Flask(__name__)


# ---------- HELPERS ----------
def run_query(sql, params=(), fetch=None, commit=False):
    """Open connection, run SQL, always close. fetch = 'all' | 'one' | 'count'."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = None
        if fetch == "all":
            result = cur.fetchall()
        elif fetch == "one":
            result = cur.fetchone()
        elif fetch == "count":
            result = cur.rowcount          # how many rows were changed
        if commit:
            conn.commit()
        cur.close()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_data():
    """JSON sent by the CLI (empty dict if nothing was sent)."""
    return request.get_json(silent=True) or {}


def missing_fields(data, fields):
    return [f for f in fields if not str(data.get(f, "")).strip()]


def error(message, code=400):
    return jsonify({"message": message}), code


def valid_date(text):
    try:
        datetime.strptime(str(text), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def valid_time(text):
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            datetime.strptime(str(text), fmt)
            return True
        except ValueError:
            pass
    return False


def check_patient(d):
    """Return an error message if the patient data is bad, else None."""
    missing = missing_fields(d, ["name", "age", "gender", "phone", "disease"])
    if missing:
        return f"Missing fields: {', '.join(missing)}"
    if not str(d["age"]).isdigit() or int(d["age"]) > 120:
        return "Age must be a number between 0 and 120"
    return None


# ---------- ERROR HANDLERS (always reply with {"message": ...}) ----------
@app.errorhandler(HTTPException)
def handle_http_error(e):
    return error(e.description, e.code)


@app.errorhandler(errors.UniqueViolation)
def handle_duplicate(e):
    return error("This record already exists", 409)


@app.errorhandler(errors.ForeignKeyViolation)
def handle_foreign_key(e):
    return error("Related record not found, or it is still in use", 400)


@app.errorhandler(psycopg2.Error)
def handle_db_error(e):
    return error("Database error: " + str(e).strip().splitlines()[0], 500)


# ---------- HOME / HEALTH ----------
@app.route("/")
def home():
    return jsonify({"message": "Hospital API is running"})


@app.route("/health")
def health():
    try:
        run_query("SELECT 1", fetch="one")
        return jsonify({"status": "Database connected"})
    except Exception as e:
        return jsonify({"status": "Database NOT connected", "error": str(e)}), 500


# ---------- DEPARTMENTS ----------
@app.route("/departments", methods=["GET"])
def get_departments():
    return jsonify(run_query("SELECT * FROM departments ORDER BY id", fetch="all"))


@app.route("/departments", methods=["POST"])
def add_department():
    d = get_data()
    if missing_fields(d, ["name"]):
        return error("Missing fields: name")
    row = run_query("INSERT INTO departments (name) VALUES (%s) RETURNING id",
                    (d["name"],), fetch="one", commit=True)
    return jsonify({"message": "Department added", "id": row["id"]}), 201


# ---------- DOCTORS ----------
@app.route("/doctors", methods=["GET"])
def get_doctors():
    rows = run_query(
        "SELECT d.id, d.name, d.phone, dep.name AS department "
        "FROM doctors d LEFT JOIN departments dep ON d.department_id = dep.id "
        "ORDER BY d.id", fetch="all")
    return jsonify(rows)


@app.route("/doctors", methods=["POST"])
def add_doctor():
    d = get_data()
    missing = missing_fields(d, ["name", "phone", "department_id"])
    if missing:
        return error(f"Missing fields: {', '.join(missing)}")
    row = run_query(
        "INSERT INTO doctors (name, phone, department_id) VALUES (%s, %s, %s) RETURNING id",
        (d["name"], d["phone"], d["department_id"]), fetch="one", commit=True)
    return jsonify({"message": "Doctor added", "id": row["id"]}), 201


@app.route("/doctors/<int:did>", methods=["DELETE"])
def delete_doctor(did):
    count = run_query("DELETE FROM doctors WHERE id = %s", (did,), fetch="count", commit=True)
    if count == 0:
        return error("Doctor not found", 404)
    return jsonify({"message": "Doctor deleted"})


@app.route("/doctors/<int:did>/schedule", methods=["GET"])
def doctor_schedule(did):
    date = request.args.get("date", "")
    if not valid_date(date):
        return error("Date must be in YYYY-MM-DD format")
    rows = run_query(
        "SELECT a.id, p.name AS patient, a.appointment_time::text AS time, a.status "
        "FROM appointments a JOIN patients p ON a.patient_id = p.id "
        "WHERE a.doctor_id = %s AND a.appointment_date = %s "
        "ORDER BY a.appointment_time",
        (did, date), fetch="all")
    return jsonify(rows)


# ---------- PATIENTS ----------
@app.route("/patients", methods=["GET"])
def get_patients():
    return jsonify(run_query("SELECT * FROM patients ORDER BY id", fetch="all"))


@app.route("/patients/search", methods=["GET"])
def search_patients():
    name = request.args.get("name", "")
    rows = run_query(
        "SELECT * FROM patients WHERE name ILIKE %s ORDER BY id",
        (f"%{name}%",), fetch="all")
    return jsonify(rows)


@app.route("/patients", methods=["POST"])
def add_patient():
    d = get_data()
    problem = check_patient(d)
    if problem:
        return error(problem)
    row = run_query(
        "INSERT INTO patients (name, age, gender, phone, disease) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (d["name"], d["age"], d["gender"], d["phone"], d["disease"]),
        fetch="one", commit=True)
    return jsonify({"message": "Patient added", "id": row["id"]}), 201


@app.route("/patients/<int:pid>", methods=["PUT"])
def update_patient(pid):
    d = get_data()
    problem = check_patient(d)
    if problem:
        return error(problem)
    count = run_query(
        "UPDATE patients SET name=%s, age=%s, gender=%s, phone=%s, disease=%s WHERE id=%s",
        (d["name"], d["age"], d["gender"], d["phone"], d["disease"], pid),
        fetch="count", commit=True)
    if count == 0:
        return error("Patient not found", 404)
    return jsonify({"message": "Patient updated"})


@app.route("/patients/<int:pid>", methods=["DELETE"])
def delete_patient(pid):
    count = run_query("DELETE FROM patients WHERE id = %s", (pid,), fetch="count", commit=True)
    if count == 0:
        return error("Patient not found", 404)
    return jsonify({"message": "Patient deleted"})


@app.route("/patients/<int:pid>/appointments", methods=["GET"])
def patient_history(pid):
    rows = run_query(
        "SELECT a.id, d.name AS doctor, a.appointment_date::text AS date, "
        "a.appointment_time::text AS time, a.status "
        "FROM appointments a JOIN doctors d ON a.doctor_id = d.id "
        "WHERE a.patient_id = %s ORDER BY a.appointment_date DESC, a.appointment_time DESC",
        (pid,), fetch="all")
    return jsonify(rows)


# ---------- APPOINTMENTS ----------
@app.route("/appointments", methods=["GET"])
def get_appointments():
    rows = run_query(
        "SELECT a.id, p.name AS patient, d.name AS doctor, "
        "a.appointment_date::text AS date, a.appointment_time::text AS time, a.status "
        "FROM appointments a "
        "JOIN patients p ON a.patient_id = p.id "
        "JOIN doctors d ON a.doctor_id = d.id "
        "ORDER BY a.appointment_date, a.appointment_time", fetch="all")
    return jsonify(rows)


@app.route("/appointments", methods=["POST"])
def add_appointment():
    d = get_data()

    # 1. validate the input
    missing = missing_fields(d, ["patient_id", "doctor_id", "date", "time"])
    if missing:
        return error(f"Missing fields: {', '.join(missing)}")
    if not str(d["patient_id"]).isdigit() or not str(d["doctor_id"]).isdigit():
        return error("patient_id and doctor_id must be numbers")
    if not valid_date(d["date"]):
        return error("Date must be in YYYY-MM-DD format")
    if not valid_time(d["time"]):
        return error("Time must be in HH:MM format")

    pid, did, date, time = int(d["patient_id"]), int(d["doctor_id"]), d["date"], d["time"]

    # 2. patient and doctor must exist
    if not run_query("SELECT id FROM patients WHERE id=%s", (pid,), fetch="one"):
        return error("Patient not found", 404)
    if not run_query("SELECT id FROM doctors WHERE id=%s", (did,), fetch="one"):
        return error("Doctor not found", 404)

    # 3. conflict checks
    if run_query(
        "SELECT id FROM appointments WHERE doctor_id=%s AND appointment_date=%s "
        "AND appointment_time=%s AND status='Scheduled'", (did, date, time), fetch="one"):
        return error("Doctor is already booked at this time", 409)

    if run_query(
        "SELECT id FROM appointments WHERE patient_id=%s AND appointment_date=%s "
        "AND appointment_time=%s AND status='Scheduled'", (pid, date, time), fetch="one"):
        return error("Patient already has an appointment at this time", 409)

    # 4. save (the unique index also protects against two people booking at once)
    try:
        row = run_query(
            "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (pid, did, date, time), fetch="one", commit=True)
    except errors.UniqueViolation:
        return error("Doctor is already booked at this time", 409)
    return jsonify({"message": "Appointment booked", "id": row["id"]}), 201


@app.route("/appointments/<int:aid>/cancel", methods=["PUT"])
def cancel_appointment(aid):
    count = run_query(
        "UPDATE appointments SET status='Cancelled' WHERE id=%s",
        (aid,), fetch="count", commit=True)
    if count == 0:
        return error("Appointment not found", 404)
    return jsonify({"message": "Appointment cancelled"})



# ---------- BILLS ----------
@app.route("/bills", methods=["GET"])
def get_bills():
    rows = run_query(
        "SELECT b.id, p.name AS patient, b.amount::float AS amount, "
        "b.status, b.created_at::text AS date "
        "FROM bills b JOIN patients p ON b.patient_id = p.id "
        "ORDER BY b.id", fetch="all")
    return jsonify(rows)


@app.route("/bills", methods=["POST"])
def add_bill():
    d = get_data()
    missing = missing_fields(d, ["patient_id", "amount"])
    if missing:
        return error(f"Missing fields: {', '.join(missing)}")
    if not str(d["patient_id"]).isdigit():
        return error("patient_id must be a number")
    try:
        amount = float(d["amount"])
    except (TypeError, ValueError):
        return error("Amount must be a number")
    if amount <= 0:
        return error("Amount must be greater than 0")

    if not run_query("SELECT id FROM patients WHERE id=%s", (d["patient_id"],), fetch="one"):
        return error("Patient not found", 404)

    appt_id = d.get("appointment_id")      # optional
    row = run_query(
        "INSERT INTO bills (patient_id, appointment_id, amount) VALUES (%s, %s, %s) RETURNING id",
        (d["patient_id"], appt_id, amount), fetch="one", commit=True)
    return jsonify({"message": "Bill created", "id": row["id"]}), 201


@app.route("/bills/<int:bid>/pay", methods=["PUT"])
def pay_bill(bid):
    count = run_query("UPDATE bills SET status='Paid' WHERE id=%s",
                      (bid,), fetch="count", commit=True)
    if count == 0:
        return error("Bill not found", 404)
    return jsonify({"message": "Bill marked as Paid"})


if __name__ == "__main__":
    app.run(debug=True)