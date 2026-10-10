import requests

BASE_URL = "http://127.0.0.1:5000"


def show(rows, columns):
    """Print a list of records, one per line."""
    if isinstance(rows, dict):          # the server sent an error message
        print(rows.get("message", rows))
        return
    if not rows:
        print("No records found.")
        return
    for r in rows:
        print(" | ".join(str(r[c]) for c in columns))


def say(response):
    """Print the 'message' the server sent back."""
    print(response.json().get("message"))


# ---------- PATIENTS ----------
def add_patient():
    data = {
        "name": input("Name: "),
        "age": input("Age: "),
        "gender": input("Gender: "),
        "phone": input("Phone: "),
        "disease": input("Disease: "),
    }
    say(requests.post(f"{BASE_URL}/patients", json=data))


def view_patients():
    rows = requests.get(f"{BASE_URL}/patients").json()
    show(rows, ["id", "name", "age", "gender", "phone", "disease"])


def update_patient():
    pid = input("Patient ID to update: ")
    data = {
        "name": input("New name: "),
        "age": input("New age: "),
        "gender": input("New gender: "),
        "phone": input("New phone: "),
        "disease": input("New disease: "),
    }
    say(requests.put(f"{BASE_URL}/patients/{pid}", json=data))


def delete_patient():
    pid = input("Patient ID to delete: ")
    say(requests.delete(f"{BASE_URL}/patients/{pid}"))


def search_patient():
    name = input("Enter name to search: ")
    rows = requests.get(f"{BASE_URL}/patients/search", params={"name": name}).json()
    show(rows, ["id", "name", "age", "gender", "phone", "disease"])


def patient_history():
    pid = input("Patient ID: ")
    rows = requests.get(f"{BASE_URL}/patients/{pid}/appointments").json()
    show(rows, ["id", "doctor", "date", "time", "status"])


# ---------- DEPARTMENTS ----------
def view_departments():
    rows = requests.get(f"{BASE_URL}/departments").json()
    show(rows, ["id", "name"])


def add_department():
    say(requests.post(f"{BASE_URL}/departments", json={"name": input("Department name: ")}))


# ---------- DOCTORS ----------
def add_doctor():
    view_departments()
    data = {
        "name": input("Doctor name: "),
        "phone": input("Phone: "),
        "department_id": input("Department ID: "),
    }
    say(requests.post(f"{BASE_URL}/doctors", json=data))


def view_doctors():
    rows = requests.get(f"{BASE_URL}/doctors").json()
    show(rows, ["id", "name", "phone", "department"])


def delete_doctor():
    did = input("Doctor ID to delete: ")
    say(requests.delete(f"{BASE_URL}/doctors/{did}"))


def doctor_schedule():
    did = input("Doctor ID: ")
    date = input("Date (YYYY-MM-DD): ")
    rows = requests.get(f"{BASE_URL}/doctors/{did}/schedule", params={"date": date}).json()
    show(rows, ["id", "patient", "time", "status"])


# ---------- APPOINTMENTS ----------
def book_appointment():
    data = {
        "patient_id": input("Patient ID: "),
        "doctor_id": input("Doctor ID: "),
        "date": input("Date (YYYY-MM-DD): "),
        "time": input("Time (HH:MM): "),
    }
    say(requests.post(f"{BASE_URL}/appointments", json=data))


def view_appointments():
    rows = requests.get(f"{BASE_URL}/appointments").json()
    show(rows, ["id", "patient", "doctor", "date", "time", "status"])


def cancel_appointment():
    aid = input("Appointment ID to cancel: ")
    say(requests.put(f"{BASE_URL}/appointments/{aid}/cancel"))


# ---------- BILLS ----------
def add_bill():
    data = {
        "patient_id": input("Patient ID: "),
        "amount": input("Amount: "),
    }
    appt = input("Appointment ID (press Enter to skip): ").strip()
    if appt:
        data["appointment_id"] = appt
    say(requests.post(f"{BASE_URL}/bills", json=data))


def view_bills():
    rows = requests.get(f"{BASE_URL}/bills").json()
    show(rows, ["id", "patient", "amount", "status", "date"])


def pay_bill():
    bid = input("Bill ID to mark as paid: ")
    say(requests.put(f"{BASE_URL}/bills/{bid}/pay"))


# ---------- MENU ----------
MENU = """
=========== HOSPITAL MANAGEMENT SYSTEM ===========
 PATIENTS                      DOCTORS
  1. Add Patient                8. Add Doctor
  2. View Patients              9. View Doctors
  3. Update Patient            10. Delete Doctor
  4. Delete Patient            11. Doctor Schedule
  5. Search Patient
  6. Patient History          APPOINTMENTS
                               13. Book Appointment
 DEPARTMENTS                   14. View Appointments
  7. View Departments          15. Cancel Appointment
 12. Add Department
                              BILLING
                               16. Create Bill
                               17. View Bills
                               18. Mark Bill Paid
  0. Exit
==================================================
"""

ACTIONS = {
    "1": add_patient, "2": view_patients, "3": update_patient,
    "4": delete_patient, "5": search_patient, "6": patient_history,
    "7": view_departments, "8": add_doctor, "9": view_doctors,
    "10": delete_doctor, "11": doctor_schedule, "12": add_department,
    "13": book_appointment, "14": view_appointments, "15": cancel_appointment,
    "16": add_bill, "17": view_bills, "18": pay_bill,
}


def main():
    while True:
        print(MENU)
        choice = input("Choose: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = ACTIONS.get(choice)
        if not action:
            print("Invalid choice")
            continue
        try:
            action()
        except requests.exceptions.ConnectionError:
            print("Cannot reach Flask. Is app.py running?")


main()