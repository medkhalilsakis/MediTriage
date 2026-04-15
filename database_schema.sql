-- =====================================================
-- MEDITRIAGE - COMPLETE PostgreSQL DATABASE SCHEMA
-- Generated from Django ORM Models
-- Database: PostgreSQL 12+
-- =====================================================

-- Enable UUID extension (optional, for future use)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. AUTHENTICATION APP - User Management
-- =====================================================

CREATE TABLE IF NOT EXISTS authentication_customuser (
    id BIGSERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP NOT NULL DEFAULT NOW(),
    email VARCHAR(254) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'patient' CHECK (role IN ('patient', 'doctor', 'admin')),
    phone_number VARCHAR(20) DEFAULT '',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Django M2M tables for CustomUser (from AbstractUser)
CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL,
    codename VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS authentication_customuser_groups (
    id BIGSERIAL PRIMARY KEY,
    customuser_id BIGINT NOT NULL REFERENCES authentication_customuser(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    UNIQUE(customuser_id, group_id)
);

CREATE TABLE IF NOT EXISTS authentication_customuser_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    customuser_id BIGINT NOT NULL REFERENCES authentication_customuser(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(customuser_id, permission_id)
);

-- Indexes for authentication_customuser
CREATE INDEX idx_authentication_customuser_email ON authentication_customuser(email);
CREATE INDEX idx_authentication_customuser_username ON authentication_customuser(username);
CREATE INDEX idx_authentication_customuser_role ON authentication_customuser(role);
CREATE INDEX idx_authentication_customuser_groups_customuser_id ON authentication_customuser_groups(customuser_id);
CREATE INDEX idx_authentication_customuser_groups_group_id ON authentication_customuser_groups(group_id);
CREATE INDEX idx_authentication_customuser_user_permissions_customuser_id ON authentication_customuser_user_permissions(customuser_id);
CREATE INDEX idx_authentication_customuser_user_permissions_permission_id ON authentication_customuser_user_permissions(permission_id);

-- =====================================================
-- 2. PATIENTS APP - Patient Profiles
-- =====================================================

CREATE TABLE IF NOT EXISTS patients_patientprofile (
    id BIGSERIAL PRIMARY KEY,
    dob DATE,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
    blood_group VARCHAR(3) CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    allergies TEXT DEFAULT '',
    emergency_contact_name VARCHAR(120) DEFAULT '',
    emergency_contact_phone VARCHAR(20) DEFAULT '',
    address TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL UNIQUE REFERENCES authentication_customuser(id) ON DELETE CASCADE
);

CREATE INDEX idx_patients_patientprofile_user_id ON patients_patientprofile(user_id);
CREATE INDEX idx_patients_patientprofile_blood_group ON patients_patientprofile(blood_group);
CREATE INDEX idx_patients_patientprofile_gender ON patients_patientprofile(gender);

-- =====================================================
-- 3. DOCTORS APP - Doctor Profiles & Availability
-- =====================================================

CREATE TABLE IF NOT EXISTS doctors_doctorprofile (
    id BIGSERIAL PRIMARY KEY,
    specialization VARCHAR(120) NOT NULL,
    license_number VARCHAR(80) UNIQUE NOT NULL,
    years_of_experience INTEGER NOT NULL DEFAULT 0 CHECK (years_of_experience >= 0),
    consultation_fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (consultation_fee >= 0),
    bio TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL UNIQUE REFERENCES authentication_customuser(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS doctors_doctoravailabilityslot (
    id BIGSERIAL PRIMARY KEY,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    doctor_id BIGINT NOT NULL REFERENCES doctors_doctorprofile(id) ON DELETE CASCADE,
    UNIQUE(doctor_id, weekday, start_time, end_time)
);

-- Indexes for doctors
CREATE INDEX idx_doctors_doctorprofile_user_id ON doctors_doctorprofile(user_id);
CREATE INDEX idx_doctors_doctorprofile_specialization ON doctors_doctorprofile(specialization);
CREATE INDEX idx_doctors_doctorprofile_license_number ON doctors_doctorprofile(license_number);
CREATE INDEX idx_doctors_doctoravailabilityslot_doctor_id ON doctors_doctoravailabilityslot(doctor_id);
CREATE INDEX idx_doctors_doctoravailabilityslot_weekday ON doctors_doctoravailabilityslot(weekday);

-- =====================================================================
-- 4. APPOINTMENTS APP - Appointment Scheduling
-- =====================================================================

CREATE TABLE IF NOT EXISTS appointments_appointment (
    id BIGSERIAL PRIMARY KEY,
    scheduled_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no_show')),
    urgency_level VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (urgency_level IN ('low', 'medium', 'high', 'critical')),
    reason TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    doctor_id BIGINT NOT NULL REFERENCES doctors_doctorprofile(id) ON DELETE CASCADE,
    patient_id BIGINT NOT NULL REFERENCES patients_patientprofile(id) ON DELETE CASCADE
);

-- Indexes for appointments
CREATE INDEX idx_appointments_appointment_doctor_id ON appointments_appointment(doctor_id);
CREATE INDEX idx_appointments_appointment_patient_id ON appointments_appointment(patient_id);
CREATE INDEX idx_appointments_appointment_scheduled_at ON appointments_appointment(scheduled_at);
CREATE INDEX idx_appointments_appointment_status ON appointments_appointment(status);
CREATE INDEX idx_appointments_appointment_urgency_level ON appointments_appointment(urgency_level);

-- =====================================================================
-- 5. MEDICAL_RECORDS APP - Patient Medical History & Consultations
-- =====================================================================

CREATE TABLE IF NOT EXISTS medical_records_medicalrecord (
    id BIGSERIAL PRIMARY KEY,
    chronic_conditions TEXT DEFAULT '',
    surgeries_history TEXT DEFAULT '',
    family_history TEXT DEFAULT '',
    immunizations TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    patient_id BIGINT NOT NULL UNIQUE REFERENCES patients_patientprofile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS medical_records_consultation (
    id BIGSERIAL PRIMARY KEY,
    diagnosis TEXT NOT NULL,
    vitals JSONB,
    anamnesis TEXT DEFAULT '',
    icd10_code VARCHAR(20) DEFAULT '',
    treatment_plan TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    appointment_id BIGINT UNIQUE REFERENCES appointments_appointment(id) ON DELETE SET NULL,
    doctor_id BIGINT NOT NULL REFERENCES doctors_doctorprofile(id) ON DELETE CASCADE,
    medical_record_id BIGINT NOT NULL REFERENCES medical_records_medicalrecord(id) ON DELETE CASCADE
);

-- Indexes for medical_records
CREATE INDEX idx_medical_records_medicalrecord_patient_id ON medical_records_medicalrecord(patient_id);
CREATE INDEX idx_medical_records_consultation_doctor_id ON medical_records_consultation(doctor_id);
CREATE INDEX idx_medical_records_consultation_medical_record_id ON medical_records_consultation(medical_record_id);
CREATE INDEX idx_medical_records_consultation_appointment_id ON medical_records_consultation(appointment_id);
CREATE INDEX idx_medical_records_consultation_created_at ON medical_records_consultation(created_at);

-- =====================================================================
-- 6. PRESCRIPTIONS APP - Prescription Management & PDF Generation
-- =====================================================================

CREATE TABLE IF NOT EXISTS prescriptions_prescription (
    id BIGSERIAL PRIMARY KEY,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    consultation_id BIGINT NOT NULL UNIQUE REFERENCES medical_records_consultation(id) ON DELETE CASCADE,
    doctor_id BIGINT NOT NULL REFERENCES doctors_doctorprofile(id) ON DELETE CASCADE,
    patient_id BIGINT NOT NULL REFERENCES patients_patientprofile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prescriptions_prescriptionitem (
    id BIGSERIAL PRIMARY KEY,
    medication VARCHAR(150) NOT NULL,
    dosage VARCHAR(80) NOT NULL,
    frequency VARCHAR(80) NOT NULL,
    duration VARCHAR(80) NOT NULL,
    instructions TEXT DEFAULT '',
    prescription_id BIGINT NOT NULL REFERENCES prescriptions_prescription(id) ON DELETE CASCADE
);

-- Indexes for prescriptions
CREATE INDEX idx_prescriptions_prescription_doctor_id ON prescriptions_prescription(doctor_id);
CREATE INDEX idx_prescriptions_prescription_patient_id ON prescriptions_prescription(patient_id);
CREATE INDEX idx_prescriptions_prescription_consultation_id ON prescriptions_prescription(consultation_id);
CREATE INDEX idx_prescriptions_prescription_created_at ON prescriptions_prescription(created_at);
CREATE INDEX idx_prescriptions_prescriptionitem_prescription_id ON prescriptions_prescriptionitem(prescription_id);

-- =====================================================================
-- 7. CHATBOT APP - AI Symptom Analysis & Triage
-- =====================================================================

CREATE TABLE IF NOT EXISTS chatbot_chebotsession (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(120) DEFAULT '',
    is_closed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    patient_id BIGINT NOT NULL REFERENCES patients_patientprofile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chatbot_chatbotmessage (
    id BIGSERIAL PRIMARY KEY,
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('patient', 'bot')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id BIGINT NOT NULL REFERENCES chatbot_chebotsession(id) ON DELETE CASCADE
);

-- Indexes for chatbot
CREATE INDEX idx_chatbot_chebotsession_patient_id ON chatbot_chebotsession(patient_id);
CREATE INDEX idx_chatbot_chebotsession_created_at ON chatbot_chebotsession(created_at);
CREATE INDEX idx_chatbot_chatbotmessage_session_id ON chatbot_chatbotmessage(session_id);
CREATE INDEX idx_chatbot_chatbotmessage_sender ON chatbot_chatbotmessage(sender);
CREATE INDEX idx_chatbot_chatbotmessage_created_at ON chatbot_chatbotmessage(created_at);

-- =====================================================================
-- 8. FOLLOW_UP APP - Post-Consultation Follow-up Appointments
-- =====================================================================

CREATE TABLE IF NOT EXISTS follow_up_followup (
    id BIGSERIAL PRIMARY KEY,
    notes TEXT DEFAULT '',
    scheduled_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'missed')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    consultation_id BIGINT REFERENCES medical_records_consultation(id) ON DELETE SET NULL,
    doctor_id BIGINT NOT NULL REFERENCES doctors_doctorprofile(id) ON DELETE CASCADE,
    patient_id BIGINT NOT NULL REFERENCES patients_patientprofile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS follow_up_followupalert (
    id BIGSERIAL PRIMARY KEY,
    alert_type VARCHAR(10) NOT NULL CHECK (alert_type IN ('sms', 'email', 'push')),
    scheduled_at TIMESTAMP NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    message TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    follow_up_id BIGINT NOT NULL REFERENCES follow_up_followup(id) ON DELETE CASCADE
);

-- Indexes for follow_up
CREATE INDEX idx_follow_up_followup_doctor_id ON follow_up_followup(doctor_id);
CREATE INDEX idx_follow_up_followup_patient_id ON follow_up_followup(patient_id);
CREATE INDEX idx_follow_up_followup_consultation_id ON follow_up_followup(consultation_id);
CREATE INDEX idx_follow_up_followup_scheduled_at ON follow_up_followup(scheduled_at);
CREATE INDEX idx_follow_up_followup_status ON follow_up_followup(status);
CREATE INDEX idx_follow_up_followupalert_follow_up_id ON follow_up_followupalert(follow_up_id);
CREATE INDEX idx_follow_up_followupalert_scheduled_at ON follow_up_followupalert(scheduled_at);

-- =====================================================================
-- 9. NOTIFICATIONS APP - System Notifications
-- =====================================================================

CREATE TABLE IF NOT EXISTS notifications_notification (
    id BIGSERIAL PRIMARY KEY,
    notification_type VARCHAR(20) NOT NULL CHECK (notification_type IN ('system', 'appointment', 'prescription', 'follow_up', 'chatbot')),
    title VARCHAR(120) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    recipient_id BIGINT NOT NULL REFERENCES authentication_customuser(id) ON DELETE CASCADE
);

-- Indexes for notifications
CREATE INDEX idx_notifications_notification_recipient_id ON notifications_notification(recipient_id);
CREATE INDEX idx_notifications_notification_is_read ON notifications_notification(is_read);
CREATE INDEX idx_notifications_notification_created_at ON notifications_notification(created_at);
CREATE INDEX idx_notifications_notification_notification_type ON notifications_notification(notification_type);

-- =====================================================================
-- DJANGO MIGRATIONS TRACKING TABLE
-- =====================================================================

CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- DJANGO CONTENT TYPE & SESSIONS (Optional, for standard Django features)
-- =====================================================================

CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP NOT NULL
);

-- =====================================================================
-- VIEWS (Optional, for common analytics queries)
-- =====================================================================

-- View: Active Doctors with their specialization
CREATE OR REPLACE VIEW v_active_doctors AS
SELECT 
    d.id,
    u.email,
    u.first_name,
    u.last_name,
    d.specialization,
    d.license_number,
    d.years_of_experience,
    d.consultation_fee
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser u ON d.user_id = u.id
WHERE u.is_active = true;

-- View: Unread Notifications by User
CREATE OR REPLACE VIEW v_unread_notifications AS
SELECT 
    n.id,
    u.email,
    u.first_name,
    n.notification_type,
    n.title,
    n.message,
    n.created_at
FROM notifications_notification n
INNER JOIN authentication_customuser u ON n.recipient_id = u.id
WHERE n.is_read = false
ORDER BY n.created_at DESC;

-- View: Upcoming Appointments
CREATE OR REPLACE VIEW v_upcoming_appointments AS
SELECT 
    a.id,
    a.scheduled_at,
    a.status,
    a.urgency_level,
    pu.email AS patient_email,
    pu.first_name AS patient_first_name,
    pu.last_name AS patient_last_name,
    du.email AS doctor_email,
    du.first_name AS doctor_first_name,
    du.last_name AS doctor_last_name,
    doc.specialization
FROM appointments_appointment a
INNER JOIN patients_patientprofile pat ON a.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON a.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE a.scheduled_at > NOW() AND a.status IN ('pending', 'confirmed')
ORDER BY a.scheduled_at ASC;

-- View: Patient Statistics
CREATE OR REPLACE VIEW v_patient_statistics AS
SELECT 
    p.id,
    u.email,
    u.first_name,
    u.last_name,
    COUNT(DISTINCT a.id) AS total_appointments,
    COUNT(DISTINCT c.id) AS total_consultations,
    COUNT(DISTINCT pr.id) AS total_prescriptions
FROM patients_patientprofile p
INNER JOIN authentication_customuser u ON p.user_id = u.id
LEFT JOIN appointments_appointment a ON p.id = a.patient_id
LEFT JOIN medical_records_consultation c ON p.id IN (SELECT patient_id FROM medical_records_medicalrecord WHERE patient_id = p.id)
LEFT JOIN prescriptions_prescription pr ON p.id = pr.patient_id
GROUP BY p.id, u.id, u.email, u.first_name, u.last_name;

-- =====================================================================
-- SAMPLE DATA INSERTION (Optional, for testing)
-- =====================================================================

-- NOTE: Uncomment and modify as needed for testing

-- Insert sample admin user
-- INSERT INTO authentication_customuser 
-- (password, username, email, first_name, last_name, role, is_staff, is_superuser, is_active, is_verified, date_joined, created_at, updated_at)
-- VALUES 
-- ('pbkdf2_sha256$600000$...hashed_password...', 'admin', 'admin@meditriage.com', 'Admin', 'User', 'admin', true, true, true, true, NOW(), NOW(), NOW());

-- =====================================================================
-- GRANTS AND PERMISSIONS (for PostgreSQL user)
-- =====================================================================

-- Grant all privileges to a specific database user (uncomment and modify)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO meditriage_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO meditriage_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO meditriage_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO meditriage_user;

-- =====================================================================
-- END OF DATABASE SCHEMA
-- =====================================================================
