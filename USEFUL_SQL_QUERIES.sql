-- =====================================================
-- MEDITRIAGE - USEFUL SQL QUERIES
-- Requêtes pratiques pour exploitation BD
-- =====================================================

-- =====================================================
-- 1. STATISTIQUES GÉNÉRALES
-- =====================================================

-- Total utilisateurs par rôle
SELECT 
    role,
    COUNT(*) as total
FROM authentication_customuser
WHERE is_active = true
GROUP BY role
ORDER BY total DESC;

-- Utilisateurs enregistrés ce mois-ci
SELECT 
    DATE_TRUNC('month', created_at)::DATE as month,
    COUNT(*) as new_users
FROM authentication_customuser
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;

-- Compte utilisateurs actifs vs inactifs
SELECT 
    is_active,
    COUNT(*) as count
FROM authentication_customuser
GROUP BY is_active;

-- =====================================================
-- 2. REQUÊTES PATIENTS
-- =====================================================

-- Tous les patients avec détails
SELECT 
    p.id,
    u.email,
    u.first_name,
    u.last_name,
    p.dob,
    p.gender,
    p.blood_group,
    p.allergies
FROM patients_patientprofile p
INNER JOIN authentication_customuser u ON p.user_id = u.id
WHERE u.is_active = true
ORDER BY p.created_at DESC;

-- Patients avec groupe sanguin spécifique
SELECT 
    u.email,
    u.first_name,
    p.blood_group
FROM patients_patientprofile p
INNER JOIN authentication_customuser u ON p.user_id = u.id
WHERE p.blood_group = 'O+'
ORDER BY u.first_name;

-- Patients avec allergies documentées
SELECT 
    u.email,
    u.first_name,
    p.allergies
FROM patients_patientprofile p
INNER JOIN authentication_customuser u ON p.user_id = u.id
WHERE p.allergies != ''
ORDER BY u.first_name;

-- Patients non utilisés depuis plus de 30 jours
SELECT 
    u.email,
    u.first_name,
    MAX(CASE 
        WHEN u.last_login > a.updated_at THEN u.last_login 
        ELSE a.updated_at 
    END) as last_activity
FROM patients_patientprofile p
INNER JOIN authentication_customuser u ON p.user_id = u.id
LEFT JOIN appointments_appointment a ON p.id = a.patient_id
WHERE u.is_active = true
GROUP BY u.id, u.email, u.first_name
HAVING MAX(CASE 
    WHEN u.last_login > a.updated_at THEN u.last_login 
    ELSE a.updated_at 
END) < NOW() - INTERVAL '30 days'
ORDER BY last_activity DESC;

-- =====================================================
-- 3. REQUÊTES MÉDECINS
-- =====================================================

-- Tous les médecins avec spécialité
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
WHERE u.is_active = true
ORDER BY d.specialization;

-- Médecins par spécialité
SELECT 
    d.specialization,
    COUNT(*) as count,
    AVG(d.years_of_experience) as avg_experience,
    AVG(d.consultation_fee) as avg_fee
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser u ON d.user_id = u.id
WHERE u.is_active = true
GROUP BY d.specialization
ORDER BY count DESC;

-- Médecin avec plus d'expérience
SELECT 
    u.email,
    u.first_name,
    d.specialization,
    d.years_of_experience
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser u ON d.user_id = u.id
WHERE u.is_active = true
ORDER BY d.years_of_experience DESC
LIMIT 10;

-- Créneaux disponibilité pour semaine
SELECT 
    u.first_name,
    u.last_name,
    d.specialization,
    CASE das.weekday
        WHEN 0 THEN 'Lundi'
        WHEN 1 THEN 'Mardi'
        WHEN 2 THEN 'Mercredi'
        WHEN 3 THEN 'Jeudi'
        WHEN 4 THEN 'Vendredi'
        WHEN 5 THEN 'Samedi'
        WHEN 6 THEN 'Dimanche'
    END as day,
    das.start_time,
    das.end_time
FROM doctors_doctoravailabilityslot das
INNER JOIN doctors_doctorprofile d ON das.doctor_id = d.id
INNER JOIN authentication_customuser u ON d.user_id = u.id
WHERE das.is_active = true AND u.is_active = true
ORDER BY das.weekday, das.start_time;

-- Médecins sans créneaux définis
SELECT 
    u.email,
    u.first_name,
    d.specialization
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser u ON d.user_id = u.id
LEFT JOIN doctors_doctoravailabilityslot das ON d.id = das.doctor_id
WHERE u.is_active = true AND das.id IS NULL
ORDER BY u.first_name;

-- =====================================================
-- 4. RENDEZ-VOUS (APPOINTMENTS)
-- =====================================================

-- Tous les rendez-vous à venir
SELECT 
    a.id,
    a.scheduled_at,
    a.status,
    a.urgency_level,
    pu.email as patient_email,
    p.first_name as patient_first_name,
    du.email as doctor_email,
    d.specialization,
    a.reason
FROM appointments_appointment a
INNER JOIN patients_patientprofile pat ON a.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON a.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE a.scheduled_at > NOW() AND a.status IN ('pending', 'confirmed')
ORDER BY a.scheduled_at ASC;

-- Rendez-vous d'aujourd'hui
SELECT 
    a.id,
    a.scheduled_at::TIME as time,
    a.status,
    a.urgency_level,
    pu.email as patient_email,
    pu.first_name as patient_name,
    d.specialization
FROM appointments_appointment a
INNER JOIN patients_patientprofile pat ON a.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON a.doctor_id = doc.id
WHERE DATE(a.scheduled_at) = CURRENT_DATE
ORDER BY a.scheduled_at ASC;

-- RDV urgents (critical/high)
SELECT 
    a.id,
    a.scheduled_at,
    a.urgency_level,
    pu.email as patient_email,
    du.email as doctor_email,
    d.specialization
FROM appointments_appointment a
INNER JOIN patients_patientprofile pat ON a.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON a.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE a.urgency_level IN ('critical', 'high')
AND a.status != 'cancelled'
ORDER BY a.urgency_level DESC, a.scheduled_at ASC;

-- Taux complétude RDV par médecin
SELECT 
    du.email,
    du.first_name,
    COUNT(*) as total_appointments,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed,
    ROUND(100.0 * COUNT(CASE WHEN a.status = 'completed' THEN 1 END) / COUNT(*), 2) as completion_rate
FROM appointments_appointment a
INNER JOIN doctors_doctorprofile doc ON a.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
GROUP BY du.id, du.email, du.first_name
ORDER BY completion_rate DESC;

-- =====================================================
-- 5. DOSSIERS MÉDICAUX & CONSULTATIONS
-- =====================================================

-- Tous les dossiers médicaux
SELECT 
    mr.id,
    u.email,
    u.first_name,
    mr.chronic_conditions,
    mr.surgeries_history,
    mr.family_history
FROM medical_records_medicalrecord mr
INNER JOIN patients_patientprofile p ON mr.patient_id = p.id
INNER JOIN authentication_customuser u ON p.user_id = u.id
ORDER BY u.first_name;

-- Consultations récentes
SELECT 
    c.id,
    c.created_at,
    pu.email as patient_email,
    du.email as doctor_email,
    c.diagnosis,
    c.icd10_code,
    c.vitals
FROM medical_records_consultation c
INNER JOIN medical_records_medicalrecord mr ON c.medical_record_id = mr.id
INNER JOIN patients_patientprofile p ON mr.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON c.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
ORDER BY c.created_at DESC
LIMIT 20;

-- Codes ICD-10 les plus utilisés
SELECT 
    icd10_code,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM medical_records_consultation
WHERE icd10_code != ''
GROUP BY icd10_code
ORDER BY count DESC
LIMIT 20;

-- Consultation sans ordonnance
SELECT 
    c.id,
    c.created_at,
    pu.email as patient_email,
    du.email as doctor_email
FROM medical_records_consultation c
INNER JOIN medical_records_medicalrecord mr ON c.medical_record_id = mr.id
INNER JOIN patients_patientprofile p ON mr.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON c.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
LEFT JOIN prescriptions_prescription pr ON c.id = pr.consultation_id
WHERE pr.id IS NULL
ORDER BY c.created_at DESC;

-- =====================================================
-- 6. ORDONNANCES (PRESCRIPTIONS)
-- =====================================================

-- Toutes les ordonnances
SELECT 
    p.id,
    p.created_at,
    pu.email as patient_email,
    du.email as doctor_email,
    COUNT(pi.id) as medication_count,
    p.notes
FROM prescriptions_prescription p
INNER JOIN patients_patientprofile pat ON p.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON p.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
LEFT JOIN prescriptions_prescriptionitem pi ON p.id = pi.prescription_id
GROUP BY p.id, p.created_at, pu.email, du.email, p.notes
ORDER BY p.created_at DESC;

-- Détail ordonnances avec médicaments
SELECT 
    p.id as prescription_id,
    pu.email as patient_email,
    pi.medication,
    pi.dosage,
    pi.frequency,
    pi.duration,
    pi.instructions
FROM prescriptions_prescription p
INNER JOIN patients_patientprofile pat ON p.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
INNER JOIN prescriptions_prescriptionitem pi ON p.id = pi.prescription_id
ORDER BY p.id, pi.medication;

-- Médicaments les plus prescrits
SELECT 
    pi.medication,
    COUNT(*) as times_prescribed,
    STRING_AGG(DISTINCT pi.dosage, ', ') as dosages
FROM prescriptions_prescriptionitem pi
GROUP BY pi.medication
ORDER BY times_prescribed DESC
LIMIT 20;

-- Ordonnances du mois dernier
SELECT 
    p.id,
    p.created_at::DATE as date,
    pu.email as patient_email,
    COUNT(pi.id) as medication_count
FROM prescriptions_prescription p
INNER JOIN patients_patientprofile pat ON p.patient_id = pat.id
INNER JOIN authentication_customuser pu ON pat.user_id = pu.id
LEFT JOIN prescriptions_prescriptionitem pi ON p.id = pi.prescription_id
WHERE p.created_at > NOW() - INTERVAL '30 days'
GROUP BY p.id, p.created_at, pu.email
ORDER BY p.created_at DESC;

-- =====================================================
-- 7. SESSIONS CHATBOT (IA)
-- =====================================================

-- Sessions chatbot actives
SELECT 
    cs.id,
    cs.created_at,
    pu.email as patient_email,
    COUNT(cm.id) as message_count,
    MAX(cm.created_at) as last_message
FROM chatbot_chebotsession cs
INNER JOIN patients_patientprofile p ON cs.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
LEFT JOIN chatbot_chatbotmessage cm ON cs.id = cm.session_id
WHERE cs.is_closed = false
GROUP BY cs.id, cs.created_at, pu.email
ORDER BY MAX(cm.created_at) DESC;

-- Messages chatbot d'une session
SELECT 
    cm.id,
    cm.created_at,
    cm.sender,
    cm.content,
    cm.metadata
FROM chatbot_chatbotmessage cm
WHERE cm.session_id = $1  -- Remplacer $1 par session_id
ORDER BY cm.created_at ASC;

-- Sessions chatbot fermées ce mois
SELECT 
    cs.id,
    cs.created_at,
    cs.updated_at,
    pu.email as patient_email,
    COUNT(DISTINCT cm.id) as total_messages
FROM chatbot_chebotsession cs
INNER JOIN patients_patientprofile p ON cs.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
LEFT JOIN chatbot_chatbotmessage cm ON cs.id = cm.session_id
WHERE cs.is_closed = true
AND cs.updated_at > NOW() - INTERVAL '30 days'
GROUP BY cs.id, cs.created_at, cs.updated_at, pu.email
ORDER BY cs.updated_at DESC;

-- =====================================================
-- 8. SUIVI (FOLLOW-UP)
-- =====================================================

-- Suivis à venir
SELECT 
    fu.id,
    fu.scheduled_at,
    fu.status,
    pu.email as patient_email,
    du.email as doctor_email,
    fu.notes
FROM follow_up_followup fu
INNER JOIN patients_patientprofile p ON fu.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON fu.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE fu.scheduled_at > NOW()
AND fu.status IN ('scheduled', 'in_progress')
ORDER BY fu.scheduled_at ASC;

-- Suivis d'astheure
SELECT 
    fu.id,
    fu.scheduled_at::TIME,
    fu.status,
    pu.email as patient_email,
    du.email as doctor_email
FROM follow_up_followup fu
INNER JOIN patients_patientprofile p ON fu.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON fu.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE DATE(fu.scheduled_at) = CURRENT_DATE
ORDER BY fu.scheduled_at ASC;

-- Suivis manqués
SELECT 
    fu.id,
    fu.scheduled_at,
    pu.email as patient_email,
    du.email as doctor_email,
    fu.notes
FROM follow_up_followup fu
INNER JOIN patients_patientprofile p ON fu.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
INNER JOIN doctors_doctorprofile doc ON fu.doctor_id = doc.id
INNER JOIN authentication_customuser du ON doc.user_id = du.id
WHERE fu.status = 'missed'
ORDER BY fu.scheduled_at DESC;

-- Alertes suivi non envoyées
SELECT 
    fua.id,
    fua.scheduled_at,
    fua.alert_type,
    pu.email as patient_email,
    fua.message
FROM follow_up_followupalert fua
INNER JOIN follow_up_followup fu ON fua.follow_up_id = fu.id
INNER JOIN patients_patientprofile p ON fu.patient_id = p.id
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
WHERE fua.status = 'pending'
AND fua.scheduled_at <= NOW()
ORDER BY fua.scheduled_at ASC;

-- =====================================================
-- 9. NOTIFICATIONS
-- =====================================================

-- Notifications non lues par utilisateur
SELECT 
    n.id,
    n.created_at,
    n.notification_type,
    n.title,
    n.message,
    u.email
FROM notifications_notification n
INNER JOIN authentication_customuser u ON n.recipient_id = u.id
WHERE n.is_read = false
ORDER BY n.created_at DESC;

-- Résumé notifications par type
SELECT 
    notification_type,
    COUNT(*) as total,
    COUNT(CASE WHEN is_read = false THEN 1 END) as unread,
    ROUND(100.0 * COUNT(CASE WHEN is_read = false THEN 1 END) / COUNT(*), 2) as unread_rate
FROM notifications_notification
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY notification_type
ORDER BY total DESC;

-- Historique notifications d'un utilisateur
SELECT 
    n.id,
    n.created_at,
    n.notification_type,
    n.title,
    n.is_read
FROM notifications_notification n
WHERE n.recipient_id = $1  -- Remplacer $1 par user_id
ORDER BY n.created_at DESC
LIMIT 50;

-- =====================================================================
-- 10. RAPPORTS & ANALYTICS
-- =====================================================================

-- Activité mensuelle
SELECT 
    DATE_TRUNC('month', a.created_at)::DATE as month,
    COUNT(DISTINCT a.patient_id) as unique_patients,
    COUNT(DISTINCT a.doctor_id) as unique_doctors,
    COUNT(*) as total_appointments
FROM appointments_appointment a
GROUP BY DATE_TRUNC('month', a.created_at)
ORDER BY month DESC;

-- Taux de complétude RDV
SELECT 
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM appointments_appointment
GROUP BY status
ORDER BY count DESC;

-- Distribution urgence RDV
SELECT 
    urgency_level,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM appointments_appointment
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY urgency_level
ORDER BY count DESC;

-- Patient le plus consulté
SELECT 
    p.id,
    pu.email,
    pu.first_name,
    COUNT(DISTINCT a.id) as appointment_count,
    COUNT(DISTINCT c.id) as consultation_count
FROM patients_patientprofile p
INNER JOIN authentication_customuser pu ON p.user_id = pu.id
LEFT JOIN appointments_appointment a ON p.id = a.patient_id
LEFT JOIN medical_records_consultation c ON p.id IN (
    SELECT patient_id FROM prescriptions_prescription 
    WHERE patient_id = p.id
)
GROUP BY p.id, pu.id, pu.email, pu.first_name
ORDER BY appointment_count DESC
LIMIT 10;

-- Médecin le plus sollicité
SELECT 
    d.id,
    du.email,
    du.first_name,
    d.specialization,
    COUNT(DISTINCT a.id) as appointment_count,
    COUNT(DISTINCT c.id) as consultation_count,
    AVG(d.consultation_fee) as avg_fee
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser du ON d.user_id = du.id
LEFT JOIN appointments_appointment a ON d.id = a.doctor_id
LEFT JOIN medical_records_consultation c ON d.id = c.doctor_id
GROUP BY d.id, du.id, du.email, du.first_name, d.specialization
ORDER BY appointment_count DESC
LIMIT 10;

-- =====================================================================
-- 11. NETTOYAGE & MAINTENANCE
-- =====================================================================

-- Supprimer sessions chatbot fermées depuis 90 jours
-- DELETE FROM chatbot_chebotsession 
-- WHERE is_closed = true 
-- AND updated_at < NOW() - INTERVAL '90 days';

-- Supprimer notifications lues depuis 60 jours
-- DELETE FROM notifications_notification 
-- WHERE is_read = true 
-- AND created_at < NOW() - INTERVAL '60 days';

-- Archiver RDV terminés depuis 1 an
-- CREATE TABLE appointments_archive AS
-- SELECT * FROM appointments_appointment 
-- WHERE status = 'completed' 
-- AND scheduled_at < NOW() - INTERVAL '1 year';

-- DELETE FROM appointments_appointment 
-- WHERE status = 'completed' 
-- AND scheduled_at < NOW() - INTERVAL '1 year';

-- =====================================================================
-- 12. INTÉGRITÉ & VALIDATION
-- =====================================================================

-- Vérifier orphelins (patient sans profil)
SELECT 
    u.id,
    u.email
FROM authentication_customuser u
WHERE u.role = 'patient'
AND NOT EXISTS (
    SELECT 1 FROM patients_patientprofile p WHERE p.user_id = u.id
)
ORDER BY u.created_at DESC;

-- Vérifier médecins sans consultation
SELECT 
    d.id,
    du.email,
    du.first_name,
    COUNT(a.id) as appointment_count
FROM doctors_doctorprofile d
INNER JOIN authentication_customuser du ON d.user_id = du.id
LEFT JOIN appointments_appointment a ON d.id = a.doctor_id
GROUP BY d.id, du.id, du.email, du.first_name
HAVING COUNT(DISTINCT c.id) = 0;

-- Vérifier RDV sans patient/médecin
SELECT 
    a.id,
    a.scheduled_at
FROM appointments_appointment a
WHERE a.patient_id NOT IN (SELECT id FROM patients_patientprofile)
OR a.doctor_id NOT IN (SELECT id FROM doctors_doctorprofile);

-- =====================================================================
-- FIN DES REQUÊTES UTILES
-- =====================================================================
