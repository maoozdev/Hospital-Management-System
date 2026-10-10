CREATE TABLE IF NOT EXISTS bills (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id INT REFERENCES appointments(id) ON DELETS SET NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    status VARCHAR(10) NOT NULL DERAULT 'Unpaid',
    created_at DATE NOT NULL DEFAULT CURRENT_DATE

);