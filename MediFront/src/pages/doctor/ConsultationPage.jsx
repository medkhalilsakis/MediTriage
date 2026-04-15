import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getAppointmentById, listAppointments } from '../../api/appointmentsApi'
import { listDoctorProfiles } from '../../api/doctorsApi'
import {
  createConsultationFromAppointment,
  getMedicalRecord,
  listConsultations,
  referFromConsultation,
  scheduleFollowUpFromConsultation,
  updateConsultation,
  updateMedicalRecord,
} from '../../api/medicalRecordsApi'
import { useAuthStore } from '../../store/authStore'

const INITIAL_DOSSIER_FORM = {
  diagnosis: '',
  anamnesis: '',
  treatment_plan: '',
  consultation_motive: '',
  medical_background: '',
  administrative_notes: '',
  clinical_examination: '',
  complementary_exams: '',
  follow_up_plan: '',
  annex_notes: '',
  social_security_number: '',
  chronic_conditions: '',
  surgeries_history: '',
  family_history: '',
  immunizations: '',
}

const INITIAL_FOLLOW_UP_DRAFT = {
  scheduled_at: '',
  reason: 'Follow-up consultation',
  notes: '',
}

const INITIAL_REFERRAL_DRAFT = {
  department: '',
  target_doctor_id: '',
  scheduled_at: '',
  reason: 'Specialist referral',
  notes: '',
}

const INITIAL_SPECIALTY_ASSESSMENT_DRAFT = {
  confidence_level: 'medium',
  opinion: '',
}

const INITIAL_METRIC_DRAFT = {
  metric_type: 'blood_pressure',
  recorded_at: '',
  period_start: '',
  period_end: '',
  value_primary: '',
  value_secondary: '',
  unit: 'mmHg',
  notes: '',
}

const SLOT_DURATION_MINUTES = 30

const SPECIALTY_CHECKLIST_MAP = {
  general_medicine: [
    { id: 'triage_reviewed', label: 'Triage reviewed and validated' },
    { id: 'bp_screening', label: 'Blood pressure risk screening completed' },
    { id: 'glucose_screening', label: 'Diabetes risk screening completed' },
    { id: 'lifestyle_assessment', label: 'Lifestyle risk factors evaluated' },
    { id: 'chronic_followup_needed', label: 'Chronic follow-up pathway needed' },
  ],
  cardiology: [
    { id: 'ecg_reviewed', label: 'ECG interpretation documented' },
    { id: 'hypertension_stage_checked', label: 'Hypertension stage classified' },
    { id: 'heart_failure_signs', label: 'Heart failure signs assessed' },
    { id: 'lipid_risk_profile', label: 'Cardiovascular risk profile reviewed' },
  ],
  endocrinology: [
    { id: 'hba1c_checked', label: 'HbA1c trend reviewed' },
    { id: 'glycemic_targets_defined', label: 'Glycemic targets defined' },
    { id: 'insulin_strategy_reviewed', label: 'Insulin/therapy strategy reviewed' },
    { id: 'complication_screening', label: 'Complications screening planned' },
  ],
  neurology: [
    { id: 'neuro_exam_completed', label: 'Neurological exam completed' },
    { id: 'stroke_red_flags', label: 'Stroke red flags checked' },
    { id: 'motor_sensory_tracking', label: 'Motor and sensory tracking updated' },
  ],
  respiratory: [
    { id: 'oxygenation_reviewed', label: 'Oxygenation and dyspnea assessed' },
    { id: 'spirometry_indication', label: 'Spirometry indication documented' },
    { id: 'inhaler_technique', label: 'Inhaler strategy reviewed' },
  ],
  gastroenterology: [
    { id: 'abdominal_exam', label: 'Abdominal exam findings documented' },
    { id: 'liver_panel_reviewed', label: 'Liver and GI lab panel reviewed' },
    { id: 'nutrition_flags', label: 'Nutrition and weight changes assessed' },
  ],
  dermatology: [
    { id: 'lesion_mapping', label: 'Lesion mapping documented' },
    { id: 'infection_screening', label: 'Infection and inflammation screened' },
    { id: 'skin_treatment_plan', label: 'Skin treatment strategy updated' },
  ],
}

const METRIC_CONFIG = {
  blood_pressure: { label: 'Blood Pressure', defaultUnit: 'mmHg', primaryLabel: 'Systolic', secondaryLabel: 'Diastolic' },
  glucose: { label: 'Blood Glucose', defaultUnit: 'g/L', primaryLabel: 'Glucose', secondaryLabel: 'Optional second value' },
  hba1c: { label: 'HbA1c', defaultUnit: '%', primaryLabel: 'HbA1c', secondaryLabel: 'Optional second value' },
  weight: { label: 'Weight', defaultUnit: 'kg', primaryLabel: 'Weight', secondaryLabel: 'Optional second value' },
  custom: { label: 'Custom metric', defaultUnit: '', primaryLabel: 'Primary value', secondaryLabel: 'Secondary value (optional)' },
}

const toDateTimeInput = (value) => {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

const normalizeDateTimeLocalToSlot = (value) => {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  date.setSeconds(0, 0)
  const remainder = date.getMinutes() % SLOT_DURATION_MINUTES
  if (remainder !== 0) {
    date.setMinutes(date.getMinutes() + (SLOT_DURATION_MINUTES - remainder))
  }

  return toDateTimeInput(date.toISOString())
}

const normalizeDateTimeLocalToIso = (value) => {
  const normalizedInput = normalizeDateTimeLocalToSlot(value)
  if (!normalizedInput) {
    return null
  }

  const date = new Date(normalizedInput)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  return date.toISOString()
}

const normalizeDateOnly = (value) => {
  if (!value) {
    return ''
  }
  return String(value).slice(0, 10)
}

const toNumberOrNull = (value) => {
  if (value === '' || value === null || value === undefined) {
    return null
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const extractApiError = (error, fallback) => {
  const responseData = error?.response?.data
  const detail = responseData?.detail
  if (detail) {
    return String(detail)
  }

  if (responseData && typeof responseData === 'object') {
    const firstFieldError = Object.values(responseData)[0]
    if (firstFieldError) {
      return Array.isArray(firstFieldError) ? firstFieldError.join(', ') : String(firstFieldError)
    }
  }

  return fallback
}

function ConsultationPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const [searchParams, setSearchParams] = useSearchParams()

  const initialAppointmentId = searchParams.get('appointment') || ''
  const [selectedAppointmentId, setSelectedAppointmentId] = useState(initialAppointmentId)
  const [dossierForm, setDossierForm] = useState(INITIAL_DOSSIER_FORM)
  const [followUpDraft, setFollowUpDraft] = useState(INITIAL_FOLLOW_UP_DRAFT)
  const [referralDraft, setReferralDraft] = useState(INITIAL_REFERRAL_DRAFT)
  const [specialtyAssessmentDraft, setSpecialtyAssessmentDraft] = useState(INITIAL_SPECIALTY_ASSESSMENT_DRAFT)
  const [selectedChecklistIds, setSelectedChecklistIds] = useState([])
  const [metricDraft, setMetricDraft] = useState(INITIAL_METRIC_DRAFT)
  const [createdPayload, setCreatedPayload] = useState(null)
  const [hydratedConsultationId, setHydratedConsultationId] = useState(null)

  const appointmentsQuery = useQuery({ queryKey: ['doctor-consultation-appointments'], queryFn: listAppointments })

  const selectedAppointmentQuery = useQuery({
    queryKey: ['doctor-consultation-appointment', selectedAppointmentId],
    queryFn: () => getAppointmentById(selectedAppointmentId),
    enabled: Boolean(selectedAppointmentId),
  })

  const consultationsQuery = useQuery({
    queryKey: ['doctor-consultation-by-appointment', selectedAppointmentId],
    queryFn: () => listConsultations({ appointment: selectedAppointmentId }),
    enabled: Boolean(selectedAppointmentId),
  })

  const doctorsQuery = useQuery({ queryKey: ['doctor-profiles'], queryFn: listDoctorProfiles })

  const createFromAppointmentMutation = useMutation({
    mutationFn: createConsultationFromAppointment,
    onSuccess: (payload) => {
      setCreatedPayload(payload)
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      queryClient.invalidateQueries({ queryKey: ['doctor-consultations'] })
      queryClient.invalidateQueries({ queryKey: ['doctor-medical-records'] })
      toast.success(payload?.created ? 'Medical dossier created from appointment.' : 'Medical dossier already existed and was loaded.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to create medical dossier from this appointment.')),
  })

  const updateConsultationMutation = useMutation({
    mutationFn: ({ consultationId, payload }) => updateConsultation(consultationId, payload),
  })

  const updateRecordMutation = useMutation({
    mutationFn: ({ recordId, payload }) => updateMedicalRecord(recordId, payload),
  })

  const scheduleFollowUpMutation = useMutation({
    mutationFn: ({ consultationId, payload }) => scheduleFollowUpFromConsultation(consultationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Follow-up appointment scheduled.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to schedule follow-up appointment.')),
  })

  const referralMutation = useMutation({
    mutationFn: ({ consultationId, payload }) => referFromConsultation(consultationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments-today'] })
      queryClient.invalidateQueries({ queryKey: ['appointments-all'] })
      toast.success('Referral appointment created successfully.')
    },
    onError: (error) => toast.error(extractApiError(error, 'Unable to create referral appointment.')),
  })

  const allAppointments = appointmentsQuery.data?.results || appointmentsQuery.data || []
  const appointmentOptions = useMemo(
    () => allAppointments.filter((item) => ['pending', 'confirmed', 'completed'].includes(item.status)),
    [allAppointments],
  )

  const consultations = consultationsQuery.data?.results || consultationsQuery.data || []
  const existingConsultation = consultations[0] || null

  const selectedAppointment =
    selectedAppointmentQuery.data || appointmentOptions.find((item) => String(item.id) === String(selectedAppointmentId)) || null

  const activeConsultation = createdPayload?.consultation || existingConsultation
  const activeConsultationId = activeConsultation?.id || null
  const activeMedicalRecordId = createdPayload?.medical_record?.id || activeConsultation?.medical_record || null

  const medicalRecordQuery = useQuery({
    queryKey: ['doctor-medical-record', activeMedicalRecordId],
    queryFn: () => getMedicalRecord(activeMedicalRecordId),
    enabled: Boolean(activeMedicalRecordId),
  })

  const medicalRecord = medicalRecordQuery.data || createdPayload?.medical_record || null

  const doctors = doctorsQuery.data?.results || doctorsQuery.data || []
  const doctorById = useMemo(() => {
    const mapping = {}
    doctors.forEach((doctor) => {
      mapping[doctor.id] = doctor
    })
    return mapping
  }, [doctors])

  const currentDoctorProfile = activeConsultation?.doctor ? doctorById[activeConsultation.doctor] : null
  const currentDepartment = currentDoctorProfile?.department || selectedAppointment?.department || 'general_medicine'
  const checklistOptions = SPECIALTY_CHECKLIST_MAP[currentDepartment] || SPECIALTY_CHECKLIST_MAP.general_medicine

  const departments = useMemo(() => {
    const unique = {}
    doctors.forEach((doctor) => {
      if (!unique[doctor.department]) {
        unique[doctor.department] = doctor.department_label || doctor.department
      }
    })
    return Object.entries(unique).map(([value, label]) => ({ value, label }))
  }, [doctors])

  const filteredDoctors = useMemo(() => {
    if (!referralDraft.department) {
      return doctors
    }
    return doctors.filter((doctor) => doctor.department === referralDraft.department)
  }, [doctors, referralDraft.department])

  const specialtyAssessments = useMemo(() => {
    if (!medicalRecord?.specialty_assessments || !Array.isArray(medicalRecord.specialty_assessments)) {
      return []
    }
    return [...medicalRecord.specialty_assessments].sort(
      (a, b) => new Date(b.created_at || b.recorded_at || 0) - new Date(a.created_at || a.recorded_at || 0),
    )
  }, [medicalRecord])

  const longitudinalMetrics = useMemo(() => {
    if (!medicalRecord?.longitudinal_metrics || !Array.isArray(medicalRecord.longitudinal_metrics)) {
      return []
    }
    return [...medicalRecord.longitudinal_metrics].sort(
      (a, b) => new Date(a.recorded_at || 0) - new Date(b.recorded_at || 0),
    )
  }, [medicalRecord])

  const bloodPressureChartData = useMemo(
    () => longitudinalMetrics
      .filter((entry) => entry.metric_type === 'blood_pressure' && entry.recorded_at)
      .map((entry, index) => ({
        index: index + 1,
        timestamp: new Date(entry.recorded_at).toLocaleString(),
        systolic: Number(entry.value_primary),
        diastolic: Number(entry.value_secondary),
      }))
      .filter((entry) => Number.isFinite(entry.systolic)),
    [longitudinalMetrics],
  )

  const glucoseChartData = useMemo(
    () => longitudinalMetrics
      .filter((entry) => entry.metric_type === 'glucose' && entry.recorded_at)
      .map((entry, index) => ({
        index: index + 1,
        timestamp: new Date(entry.recorded_at).toLocaleString(),
        glucose: Number(entry.value_primary),
      }))
      .filter((entry) => Number.isFinite(entry.glucose)),
    [longitudinalMetrics],
  )

  useEffect(() => {
    const appointmentFromQuery = searchParams.get('appointment') || ''
    if (appointmentFromQuery && appointmentFromQuery !== selectedAppointmentId) {
      setSelectedAppointmentId(appointmentFromQuery)
    }
  }, [searchParams, selectedAppointmentId])

  useEffect(() => {
    if (!selectedAppointment?.reason) {
      return
    }

    setDossierForm((prev) => {
      if (prev.consultation_motive) {
        return prev
      }
      return {
        ...prev,
        consultation_motive: selectedAppointment.reason,
      }
    })
  }, [selectedAppointment])

  useEffect(() => {
    if (!existingConsultation || hydratedConsultationId === existingConsultation.id) {
      return
    }

    setDossierForm((prev) => ({
      ...prev,
      diagnosis: existingConsultation.diagnosis || prev.diagnosis,
      anamnesis: existingConsultation.anamnesis || prev.anamnesis,
      treatment_plan: existingConsultation.treatment_plan || prev.treatment_plan,
    }))
    setHydratedConsultationId(existingConsultation.id)
  }, [existingConsultation, hydratedConsultationId])

  const handleAppointmentSelection = (nextAppointmentId) => {
    setSelectedAppointmentId(nextAppointmentId)
    setCreatedPayload(null)
    setHydratedConsultationId(null)
    setDossierForm(INITIAL_DOSSIER_FORM)
    setFollowUpDraft(INITIAL_FOLLOW_UP_DRAFT)
    setReferralDraft(INITIAL_REFERRAL_DRAFT)
    setSpecialtyAssessmentDraft(INITIAL_SPECIALTY_ASSESSMENT_DRAFT)
    setSelectedChecklistIds([])
    setMetricDraft(INITIAL_METRIC_DRAFT)
    if (nextAppointmentId) {
      setSearchParams({ appointment: nextAppointmentId })
    } else {
      setSearchParams({})
    }
  }

  const ensureRecordPersisted = async () => {
    if (activeMedicalRecordId && activeConsultationId) {
      return {
        medicalRecordId: activeMedicalRecordId,
        consultationId: activeConsultationId,
      }
    }

    if (!selectedAppointmentId) {
      throw new Error('Select an appointment first.')
    }

    const payload = await createFromAppointmentMutation.mutateAsync({
      appointment_id: Number(selectedAppointmentId),
      diagnosis: (dossierForm.diagnosis || '').trim() || 'Pending diagnosis',
      anamnesis: (dossierForm.anamnesis || '').trim(),
      treatment_plan: (dossierForm.treatment_plan || '').trim(),
      vitals: {},
    })

    return {
      medicalRecordId: payload?.medical_record?.id,
      consultationId: payload?.consultation?.id,
    }
  }

  const handleSaveDossier = async (event) => {
    event.preventDefault()

    if (!selectedAppointmentId) {
      toast.error('Select an appointment first.')
      return
    }

    const diagnosis = (dossierForm.diagnosis || '').trim()
    const anamnesis = (dossierForm.anamnesis || '').trim()
    const treatmentPlan = (dossierForm.treatment_plan || '').trim()

    if (!diagnosis) {
      toast.error('Diagnosis is required before saving the medical dossier.')
      return
    }

    const consultationPayload = {
      diagnosis,
      anamnesis,
      treatment_plan: treatmentPlan,
    }

    const medicalRecordPayload = {
      consultation_motive: (dossierForm.consultation_motive || '').trim(),
      medical_background: (dossierForm.medical_background || '').trim(),
      current_illness_history: anamnesis,
      administrative_notes: (dossierForm.administrative_notes || '').trim(),
      clinical_examination: (dossierForm.clinical_examination || '').trim(),
      complementary_exams: (dossierForm.complementary_exams || '').trim(),
      diagnostic_summary: diagnosis,
      treatment_management: treatmentPlan,
      follow_up_plan: (dossierForm.follow_up_plan || '').trim(),
      annex_notes: (dossierForm.annex_notes || '').trim(),
      social_security_number: (dossierForm.social_security_number || '').trim(),
      chronic_conditions: (dossierForm.chronic_conditions || '').trim(),
      surgeries_history: (dossierForm.surgeries_history || '').trim(),
      family_history: (dossierForm.family_history || '').trim(),
      immunizations: (dossierForm.immunizations || '').trim(),
    }

    try {
      const ids = await ensureRecordPersisted()

      await Promise.all([
        updateConsultationMutation.mutateAsync({
          consultationId: ids.consultationId,
          payload: consultationPayload,
        }),
        updateRecordMutation.mutateAsync({
          recordId: ids.medicalRecordId,
          payload: medicalRecordPayload,
        }),
      ])

      queryClient.invalidateQueries({ queryKey: ['doctor-consultation-by-appointment', selectedAppointmentId] })
      queryClient.invalidateQueries({ queryKey: ['doctor-consultations'] })
      queryClient.invalidateQueries({ queryKey: ['doctor-medical-record', ids.medicalRecordId] })
      queryClient.invalidateQueries({ queryKey: ['doctor-medical-records'] })
      toast.success('Medical dossier updated successfully.')
    } catch (error) {
      toast.error(extractApiError(error, 'Unable to save medical dossier.'))
    }
  }

  const handleSaveSpecialtyAssessment = async () => {
    if (!specialtyAssessmentDraft.opinion.trim()) {
      toast.error('Please add a specialist opinion before saving.')
      return
    }

    try {
      const ids = await ensureRecordPersisted()
      const existing = Array.isArray(medicalRecord?.specialty_assessments) ? medicalRecord.specialty_assessments : []

      const assessment = {
        id: `assessment-${Date.now()}`,
        created_at: new Date().toISOString(),
        doctor_id: activeConsultation?.doctor || null,
        doctor_email: activeConsultation?.doctor_email || user?.email || 'unknown-doctor',
        department: currentDepartment,
        checked_items: selectedChecklistIds,
        opinion: specialtyAssessmentDraft.opinion.trim(),
        confidence_level: specialtyAssessmentDraft.confidence_level,
      }

      await updateRecordMutation.mutateAsync({
        recordId: ids.medicalRecordId,
        payload: {
          specialty_assessments: [...existing, assessment],
        },
      })

      queryClient.invalidateQueries({ queryKey: ['doctor-medical-record', ids.medicalRecordId] })
      setSpecialtyAssessmentDraft(INITIAL_SPECIALTY_ASSESSMENT_DRAFT)
      setSelectedChecklistIds([])
      toast.success('Specialty assessment saved for multidisciplinary review.')
    } catch (error) {
      toast.error(extractApiError(error, 'Unable to save specialty assessment.'))
    }
  }

  const handleAddMetricRecord = async () => {
    const normalizedRecordedAt = normalizeDateTimeLocalToIso(metricDraft.recorded_at)
    if (!normalizedRecordedAt) {
      toast.error('Please provide a valid recorded date and time.')
      return
    }

    const valuePrimary = toNumberOrNull(metricDraft.value_primary)
    if (valuePrimary === null) {
      toast.error('Primary metric value is required.')
      return
    }

    const valueSecondary = toNumberOrNull(metricDraft.value_secondary)

    try {
      const ids = await ensureRecordPersisted()
      const existing = Array.isArray(medicalRecord?.longitudinal_metrics) ? medicalRecord.longitudinal_metrics : []

      const metricEntry = {
        id: `metric-${Date.now()}`,
        created_at: new Date().toISOString(),
        doctor_id: activeConsultation?.doctor || null,
        doctor_email: activeConsultation?.doctor_email || user?.email || 'unknown-doctor',
        metric_type: metricDraft.metric_type,
        recorded_at: normalizedRecordedAt,
        period_start: normalizeDateOnly(metricDraft.period_start),
        period_end: normalizeDateOnly(metricDraft.period_end),
        value_primary: valuePrimary,
        value_secondary: valueSecondary,
        unit: metricDraft.unit || METRIC_CONFIG[metricDraft.metric_type]?.defaultUnit || '',
        notes: metricDraft.notes.trim(),
      }

      await updateRecordMutation.mutateAsync({
        recordId: ids.medicalRecordId,
        payload: {
          longitudinal_metrics: [...existing, metricEntry],
        },
      })

      queryClient.invalidateQueries({ queryKey: ['doctor-medical-record', ids.medicalRecordId] })
      setMetricDraft((prev) => ({
        ...INITIAL_METRIC_DRAFT,
        metric_type: prev.metric_type,
        unit: METRIC_CONFIG[prev.metric_type]?.defaultUnit || '',
      }))
      toast.success('Clinical metric record added.')
    } catch (error) {
      toast.error(extractApiError(error, 'Unable to add metric record.'))
    }
  }

  const handleFollowUp = () => {
    if (!activeConsultationId) {
      toast.error('Save the consultation first before scheduling a follow-up.')
      return
    }

    if (!followUpDraft.scheduled_at) {
      toast.error('Select a follow-up date and time.')
      return
    }

    const normalizedScheduledAt = normalizeDateTimeLocalToIso(followUpDraft.scheduled_at)
    if (!normalizedScheduledAt) {
      toast.error('Invalid follow-up date and time.')
      return
    }

    scheduleFollowUpMutation.mutate(
      {
        consultationId: activeConsultationId,
        payload: {
          scheduled_at: normalizedScheduledAt,
          reason: (followUpDraft.reason || '').trim() || 'Follow-up consultation',
          notes: (followUpDraft.notes || '').trim(),
        },
      },
      {
        onSuccess: () => setFollowUpDraft(INITIAL_FOLLOW_UP_DRAFT),
      },
    )
  }

  const handleReferral = () => {
    if (!activeConsultationId) {
      toast.error('Save the consultation first before creating a referral.')
      return
    }

    if (!referralDraft.target_doctor_id) {
      toast.error('Select the target doctor for referral.')
      return
    }
    if (!referralDraft.scheduled_at) {
      toast.error('Select referral date and time.')
      return
    }

    const normalizedScheduledAt = normalizeDateTimeLocalToIso(referralDraft.scheduled_at)
    if (!normalizedScheduledAt) {
      toast.error('Invalid referral date and time.')
      return
    }

    const payload = {
      target_doctor_id: Number(referralDraft.target_doctor_id),
      scheduled_at: normalizedScheduledAt,
      reason: (referralDraft.reason || '').trim() || 'Referral consultation',
      notes: (referralDraft.notes || '').trim(),
    }
    if (referralDraft.department) {
      payload.department = referralDraft.department
    }

    referralMutation.mutate(
      {
        consultationId: activeConsultationId,
        payload,
      },
      {
        onSuccess: () => setReferralDraft(INITIAL_REFERRAL_DRAFT),
      },
    )
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Consultation and Medical Dossier Workspace</h2>
        <p className="muted">
          Professional multidisciplinary workspace: specialist assessments, longitudinal metric tracking, and coordinated follow-up/referral.
        </p>
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Appointment context</h3>
          <Link to="/doctor/dashboard" className="ghost-btn inline-action">
            Back to dashboard
          </Link>
        </div>

        <label>
          Appointment
          <select
            value={selectedAppointmentId}
            onChange={(event) => handleAppointmentSelection(event.target.value)}
          >
            <option value="">Select appointment</option>
            {appointmentOptions.map((appointment) => (
              <option key={appointment.id} value={appointment.id}>
                #{appointment.id} - {appointment.patient_email} - {new Date(appointment.scheduled_at).toLocaleString()} ({appointment.status})
              </option>
            ))}
          </select>
        </label>

        {selectedAppointment ? (
          <div className="timeline-item">
            <p>
              Patient: <strong>{selectedAppointment.patient_email}</strong>
            </p>
            <p>
              Scheduled at: <strong>{new Date(selectedAppointment.scheduled_at).toLocaleString()}</strong>
            </p>
            <p>
              Status: <span className={`status-tag ${selectedAppointment.status}`}>{selectedAppointment.status}</span>
            </p>
            <p className="muted">Current specialty context: {currentDoctorProfile?.department_label || currentDepartment}</p>
          </div>
        ) : null}
      </section>

      <section className="card">
        <div className="inline-header">
          <h3>Medical dossier form</h3>
          <span className="chip">Professional Clinical Layout</span>
        </div>

        <div className="split-grid">
          <div className="timeline-item">
            <h4>Diagnostic synthesis</h4>
            <div className="form-grid">
              <label>
                Diagnosis
                <textarea
                  value={dossierForm.diagnosis}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, diagnosis: event.target.value }))}
                  placeholder="Final doctor diagnosis"
                  required
                />
              </label>
              <label>
                Anamnesis
                <textarea
                  value={dossierForm.anamnesis}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, anamnesis: event.target.value }))}
                  placeholder="Current illness history"
                />
              </label>
              <label>
                Treatment plan
                <textarea
                  value={dossierForm.treatment_plan}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, treatment_plan: event.target.value }))}
                  placeholder="Treatment and management"
                />
              </label>
              <label>
                Clinical examination
                <textarea
                  value={dossierForm.clinical_examination}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, clinical_examination: event.target.value }))}
                  placeholder="Clinical findings"
                />
              </label>
              <button
                type="button"
                onClick={handleSaveDossier}
                disabled={
                  createFromAppointmentMutation.isPending ||
                  updateConsultationMutation.isPending ||
                  updateRecordMutation.isPending
                }
              >
                {createFromAppointmentMutation.isPending || updateConsultationMutation.isPending || updateRecordMutation.isPending
                  ? 'Saving dossier...'
                  : 'Save dossier updates'}
              </button>
            </div>
          </div>

          <div className="timeline-item">
            <h4>Continuity and risk documentation</h4>
            <div className="form-grid">
              <label>
                Consultation motive
                <textarea
                  value={dossierForm.consultation_motive}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, consultation_motive: event.target.value }))}
                  placeholder="Main reason for this consultation"
                />
              </label>
              <label>
                Chronic conditions
                <textarea
                  value={dossierForm.chronic_conditions}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, chronic_conditions: event.target.value }))}
                  placeholder="Known chronic diseases"
                />
              </label>
              <label>
                Family history
                <textarea
                  value={dossierForm.family_history}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, family_history: event.target.value }))}
                  placeholder="Relevant family history"
                />
              </label>
              <label>
                Follow-up plan notes
                <textarea
                  value={dossierForm.follow_up_plan}
                  onChange={(event) => setDossierForm((prev) => ({ ...prev, follow_up_plan: event.target.value }))}
                  placeholder="Planned follow-up strategy"
                />
              </label>
            </div>
          </div>
        </div>
      </section>

      <section className="card split-grid">
        <article className="timeline-item">
          <div className="inline-header">
            <h3>Specialty assessment</h3>
            <span className="status-tag confirmed">{currentDoctorProfile?.department_label || currentDepartment}</span>
          </div>
          <p className="muted">
            Checklist adapts to current specialty. Each saved opinion remains visible for next specialists.
          </p>

          <div className="timeline">
            {checklistOptions.map((item) => (
              <label key={item.id} className="timeline-item read" style={{ opacity: 1 }}>
                <input
                  type="checkbox"
                  checked={selectedChecklistIds.includes(item.id)}
                  onChange={(event) => {
                    if (event.target.checked) {
                      setSelectedChecklistIds((prev) => [...prev, item.id])
                    } else {
                      setSelectedChecklistIds((prev) => prev.filter((id) => id !== item.id))
                    }
                  }}
                />
                <span>{item.label}</span>
              </label>
            ))}
          </div>

          <div className="form-grid">
            <label>
              Confidence level
              <select
                value={specialtyAssessmentDraft.confidence_level}
                onChange={(event) =>
                  setSpecialtyAssessmentDraft((prev) => ({ ...prev, confidence_level: event.target.value }))
                }
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label>
              Specialist opinion
              <textarea
                value={specialtyAssessmentDraft.opinion}
                onChange={(event) =>
                  setSpecialtyAssessmentDraft((prev) => ({ ...prev, opinion: event.target.value }))
                }
                placeholder="Professional opinion for multidisciplinary continuity"
              />
            </label>
            <button
              type="button"
              onClick={handleSaveSpecialtyAssessment}
              disabled={updateRecordMutation.isPending || createFromAppointmentMutation.isPending}
            >
              Save specialty assessment
            </button>
          </div>
        </article>

        <article className="timeline-item">
          <h3>Multidisciplinary trail</h3>
          {specialtyAssessments.length === 0 ? <p className="muted">No specialist assessments yet.</p> : null}
          <div className="timeline">
            {specialtyAssessments.map((assessment) => (
              <div key={assessment.id || assessment.created_at} className="timeline-item">
                <p>
                  <strong>{assessment.doctor_email || 'Unknown doctor'}</strong>
                </p>
                <p className="muted">
                  {(assessment.department || 'specialty').replaceAll('_', ' ')} | {new Date(assessment.created_at).toLocaleString()}
                </p>
                <p>
                  Confidence: <span className={`status-tag ${assessment.confidence_level || 'medium'}`}>{assessment.confidence_level || 'medium'}</span>
                </p>
                <p>{assessment.opinion}</p>
                {Array.isArray(assessment.checked_items) && assessment.checked_items.length > 0 ? (
                  <p className="muted">Checklist: {assessment.checked_items.join(', ')}</p>
                ) : null}
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="card split-grid">
        <article className="timeline-item">
          <h3>Longitudinal clinical records</h3>
          <p className="muted">
            Add non-contiguous period records (hypertension, diabetes, HbA1c, weight, custom) to build trend visibility.
          </p>

          <div className="form-grid">
            <label>
              Metric type
              <select
                value={metricDraft.metric_type}
                onChange={(event) => {
                  const nextType = event.target.value
                  setMetricDraft((prev) => ({
                    ...prev,
                    metric_type: nextType,
                    unit: METRIC_CONFIG[nextType]?.defaultUnit || '',
                    value_secondary: nextType === 'blood_pressure' ? prev.value_secondary : '',
                  }))
                }}
              >
                {Object.entries(METRIC_CONFIG).map(([value, config]) => (
                  <option key={value} value={value}>
                    {config.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Recorded at
              <input
                type="datetime-local"
                step={1800}
                value={metricDraft.recorded_at}
                onChange={(event) =>
                  setMetricDraft((prev) => ({
                    ...prev,
                    recorded_at: normalizeDateTimeLocalToSlot(event.target.value),
                  }))
                }
              />
            </label>

            <label>
              Period start
              <input
                type="date"
                value={metricDraft.period_start}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, period_start: event.target.value }))}
              />
            </label>

            <label>
              Period end
              <input
                type="date"
                value={metricDraft.period_end}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, period_end: event.target.value }))}
              />
            </label>

            <label>
              {METRIC_CONFIG[metricDraft.metric_type]?.primaryLabel || 'Primary value'}
              <input
                type="number"
                step="0.01"
                value={metricDraft.value_primary}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, value_primary: event.target.value }))}
              />
            </label>

            <label>
              {METRIC_CONFIG[metricDraft.metric_type]?.secondaryLabel || 'Secondary value'}
              <input
                type="number"
                step="0.01"
                value={metricDraft.value_secondary}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, value_secondary: event.target.value }))}
                disabled={metricDraft.metric_type !== 'blood_pressure'}
              />
            </label>

            <label>
              Unit
              <input
                value={metricDraft.unit}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, unit: event.target.value }))}
                placeholder="Unit"
              />
            </label>

            <label>
              Notes
              <textarea
                value={metricDraft.notes}
                onChange={(event) => setMetricDraft((prev) => ({ ...prev, notes: event.target.value }))}
                placeholder="Clinical context for this metric"
              />
            </label>

            <button
              type="button"
              onClick={handleAddMetricRecord}
              disabled={updateRecordMutation.isPending || createFromAppointmentMutation.isPending}
            >
              Add metric record
            </button>
          </div>

          {longitudinalMetrics.length > 0 ? (
            <div className="timeline">
              {longitudinalMetrics.slice(-8).reverse().map((entry) => (
                <div key={entry.id || entry.created_at} className="timeline-item read" style={{ opacity: 1 }}>
                  <p>
                    <strong>{METRIC_CONFIG[entry.metric_type]?.label || entry.metric_type}</strong>
                  </p>
                  <p className="muted">
                    {entry.recorded_at ? new Date(entry.recorded_at).toLocaleString() : 'No timestamp'}
                  </p>
                  <p>
                    Value: <strong>{entry.value_primary}</strong>
                    {entry.value_secondary !== null && entry.value_secondary !== undefined ? (
                      <span> / <strong>{entry.value_secondary}</strong></span>
                    ) : null}{' '}
                    {entry.unit || ''}
                  </p>
                  {(entry.period_start || entry.period_end) ? (
                    <p className="muted">Period: {entry.period_start || '?'} to {entry.period_end || '?'}</p>
                  ) : null}
                  {entry.notes ? <p className="muted">{entry.notes}</p> : null}
                </div>
              ))}
            </div>
          ) : null}
        </article>

        <article className="timeline-item">
          <h3>Visual analytics</h3>
          {bloodPressureChartData.length > 0 ? (
            <div className="timeline-item" style={{ opacity: 1 }}>
              <h4>Hypertension trend</h4>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={bloodPressureChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="systolic" stroke="#ef5b3f" strokeWidth={2} name="Systolic" />
                  <Line type="monotone" dataKey="diastolic" stroke="#0c8a82" strokeWidth={2} name="Diastolic" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="muted">No hypertension chart yet. Add blood pressure records to visualize trend.</p>
          )}

          {glucoseChartData.length > 0 ? (
            <div className="timeline-item" style={{ opacity: 1 }}>
              <h4>Diabetes trend</h4>
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={glucoseChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" hide />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="glucose" stroke="#8a3ffc" fill="#d8c7ff" name="Glucose" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="muted">No diabetes chart yet. Add glucose records to visualize trend.</p>
          )}
        </article>
      </section>

      <section className="card split-grid doctor-dashboard-actions">
        <article className="timeline-item">
          <h3>Schedule another appointment</h3>
          <p className="muted">Create a follow-up appointment for this patient from the same consultation.</p>

          <div className="form-grid">
            <label>
              Follow-up date and time
              <input
                type="datetime-local"
                step={1800}
                value={followUpDraft.scheduled_at}
                onChange={(event) =>
                  setFollowUpDraft((prev) => ({
                    ...prev,
                    scheduled_at: normalizeDateTimeLocalToSlot(event.target.value),
                  }))
                }
              />
            </label>

            <label>
              Reason
              <input
                value={followUpDraft.reason}
                onChange={(event) => setFollowUpDraft((prev) => ({ ...prev, reason: event.target.value }))}
                placeholder="Follow-up reason"
              />
            </label>

            <label>
              Notes
              <textarea
                value={followUpDraft.notes}
                onChange={(event) => setFollowUpDraft((prev) => ({ ...prev, notes: event.target.value }))}
                placeholder="Follow-up notes"
              />
            </label>

            <button
              type="button"
              onClick={handleFollowUp}
              disabled={scheduleFollowUpMutation.isPending || !activeConsultationId}
            >
              Schedule follow-up
            </button>
          </div>
        </article>

        <article className="timeline-item">
          <h3>Redirect to another department/doctor</h3>
          <p className="muted">Use this referral form to send the patient to another specialist.</p>

          <div className="form-grid">
            <label>
              Department
              <select
                value={referralDraft.department}
                onChange={(event) =>
                  setReferralDraft((prev) => ({
                    ...prev,
                    department: event.target.value,
                    target_doctor_id: '',
                  }))
                }
              >
                <option value="">All departments</option>
                {departments.map((department) => (
                  <option key={department.value} value={department.value}>
                    {department.label}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Target doctor
              <select
                value={referralDraft.target_doctor_id}
                onChange={(event) => setReferralDraft((prev) => ({ ...prev, target_doctor_id: event.target.value }))}
              >
                <option value="">Select doctor</option>
                {filteredDoctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    {doctor.user_email} ({doctor.department_label || doctor.department})
                  </option>
                ))}
              </select>
            </label>

            <label>
              Referral date and time
              <input
                type="datetime-local"
                step={1800}
                value={referralDraft.scheduled_at}
                onChange={(event) =>
                  setReferralDraft((prev) => ({
                    ...prev,
                    scheduled_at: normalizeDateTimeLocalToSlot(event.target.value),
                  }))
                }
              />
            </label>

            <label>
              Referral reason
              <input
                value={referralDraft.reason}
                onChange={(event) => setReferralDraft((prev) => ({ ...prev, reason: event.target.value }))}
                placeholder="Referral reason"
              />
            </label>

            <label>
              Notes
              <textarea
                value={referralDraft.notes}
                onChange={(event) => setReferralDraft((prev) => ({ ...prev, notes: event.target.value }))}
                placeholder="Referral notes"
              />
            </label>

            <button
              type="button"
              onClick={handleReferral}
              disabled={referralMutation.isPending || !activeConsultationId}
            >
              Redirect patient
            </button>
          </div>
        </article>
      </section>
    </div>
  )
}

export default ConsultationPage
