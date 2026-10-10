DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS departments;

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    department_id INT REFERENCES departments(id)
);

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL CHECK (age >= 0),
    gender VARCHAR(10),
    phone VARCHAR(20),
    disease VARCHAR(200)
);

CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INT NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL DEFAULT '09:00',
    status VARCHAR(20) DEFAULT 'Scheduled'
);

CREATE UNIQUE INDEX unique_doctor_slot
ON appointments (doctor_id, appointment_date, appointment_time)
WHERE status = 'Scheduled';

-- SAMPLE DATA (order matters)
INSERT INTO departments (name) VALUES
('Cardiology'), ('Neurology'), ('General');

INSERT INTO doctors (name, phone, department_id) VALUES
('Dr. Ahmed', '0300-1111111', 1),
('Dr. Sara', '0300-2222222', 2);

INSERT INTO patients (name, age, gender, phone, disease) VALUES
('Ali', 35, 'Male', '0311-1234567', 'Fever'),
('Fatima', 28, 'Female', '03149927121', 'Migraine'),
('Wahid', 33, 'Male', '031234566667', 'Diabetes'),
('Ayesha', 22, 'Female', '0375959933', 'Cold');

INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time) VALUES
(1, 1, '2026-10-20', '10:00'),
(2, 2, '2026-10-20', '11:00');