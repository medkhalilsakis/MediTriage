import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  listConsultations,
  listMedicalDocumentRequests,
  listMedicalDocuments,
  listMedicalRecords,
  uploadMedicalDocument,
} from '../../api/medicalRecordsApi'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '')

const INITIAL_UPLOAD_DRAFT = {
  title: '',
  notes: '',
  file: null,
  document_type: 'analysis_report',
}

const resolveFileUrl = (fileUrl) => {
  if (!fileUrl) {
    return ''
  }
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) {
    return fileUrl
  }
  return `${API_ORIGIN}${fileUrl}`
}

function MedicalRecordPage() {
  const queryClient = useQueryClient()
  const [uploadDrafts, setUploadDrafts] = useState({})

  const recordsQuery = useQuery({ queryKey: ['medical-records'], queryFn: listMedicalRecords })
  const consultationsQuery = useQuery({ queryKey: ['consultations'], queryFn: listConsultations })
  const requestsQuery = useQuery({ queryKey: ['medical-document-requests'], queryFn: listMedicalDocumentRequests })
  const documentsQuery = useQuery({ queryKey: ['medical-documents'], queryFn: listMedicalDocuments })

  const uploadMutation = useMutation({
    mutationFn: ({ uploadKey, ...payload }) => uploadMedicalDocument(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['medical-documents'] })
      queryClient.invalidateQueries({ queryKey: ['medical-document-requests'] })
      toast.success('Document uploaded successfully.')
      setUploadDrafts((prev) => ({
        ...prev,
        [variables.uploadKey]: INITIAL_UPLOAD_DRAFT,
      }))
    },
    onError: (error) => {
      const detail = error?.response?.data?.detail || 'Unable to upload document.'
      toast.error(String(detail))
    },
  })

  const records = recordsQuery.data?.results || recordsQuery.data || []
  const consultations = consultationsQuery.data?.results || consultationsQuery.data || []
  const documentRequests = requestsQuery.data?.results || requestsQuery.data || []
  const documents = documentsQuery.data?.results || documentsQuery.data || []

  const requestsByRecordId = useMemo(() => {
    const mapping = {}
    documentRequests.forEach((item) => {
      if (!mapping[item.medical_record]) {
        mapping[item.medical_record] = []
      }
      mapping[item.medical_record].push(item)
    })
    return mapping
  }, [documentRequests])

  const documentsByRecordId = useMemo(() => {
    const mapping = {}
    documents.forEach((item) => {
      if (!mapping[item.medical_record]) {
        mapping[item.medical_record] = []
      }
      mapping[item.medical_record].push(item)
    })
    return mapping
  }, [documents])

  const handleUploadForRequest = (recordId, requestId) => {
    const uploadKey = `request-${requestId}`
    const draft = uploadDrafts[uploadKey] || INITIAL_UPLOAD_DRAFT
    if (!draft.file) {
      toast.error('Please choose a file before uploading.')
      return
    }

    uploadMutation.mutate({
      uploadKey,
      medical_record: recordId,
      request: requestId,
      document_type: draft.document_type,
      title: draft.title?.trim() || 'Requested medical document',
      notes: draft.notes,
      file: draft.file,
    })
  }

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Medical History</h2>
        <p className="muted">
          Review your full medical dossier, requested analyses/documents, uploaded files, and consultation chronology.
        </p>
      </section>

      <section className="card">
        <h3>Medical Dossier</h3>
        {records.length === 0 ? <p className="muted">No medical records available.</p> : null}
        {records.map((record) => (
          <article key={record.id} className="timeline-item">
            <p>
              Record ID: <strong>{record.id}</strong>
            </p>
            <p>
              Status: <span className={`status-tag ${record.status || 'active'}`}>{record.status || 'active'}</span>
            </p>

            <div className="patient-overview-grid">
              <article className="timeline-item">
                <h4>1. Administrative Information</h4>
                <p>Full name: {record.patient_full_name || 'N/A'}</p>
                <p>Phone: {record.patient_phone || 'N/A'}</p>
                <p>Address: {record.patient_address || 'N/A'}</p>
                <p>Emergency contact: {record.emergency_contact_name || 'N/A'} ({record.emergency_contact_phone || 'N/A'})</p>
              </article>

              <article className="timeline-item">
                <h4>2. Consultation motive</h4>
                <p>{record.consultation_motive || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>3. Medical history</h4>
                <p>{record.medical_background || 'N/A'}</p>
                <p className="muted">Chronic conditions: {record.chronic_conditions || 'N/A'}</p>
                <p className="muted">Surgeries: {record.surgeries_history || 'N/A'}</p>
                <p className="muted">Family history: {record.family_history || 'N/A'}</p>
                <p className="muted">Immunizations: {record.immunizations || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>4. Current illness history</h4>
                <p>{record.current_illness_history || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>5. Clinical examination</h4>
                <p>{record.clinical_examination || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>6. Complementary exams</h4>
                <p>{record.complementary_exams || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>7. Diagnosis</h4>
                <p>{record.diagnostic_summary || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>8. Treatment / management</h4>
                <p>{record.treatment_management || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>9. Follow-up plan</h4>
                <p>{record.follow_up_plan || 'N/A'}</p>
              </article>

              <article className="timeline-item">
                <h4>10. Annex notes</h4>
                <p>{record.annex_notes || 'N/A'}</p>
              </article>
            </div>

            <div className="timeline">
              <h4>Doctor document requests</h4>
              {(requestsByRecordId[record.id] || []).length === 0 ? (
                <p className="muted">No document request for this record.</p>
              ) : null}

              {(requestsByRecordId[record.id] || []).map((item) => {
                const uploadKey = `request-${item.id}`
                const draft = uploadDrafts[uploadKey] || INITIAL_UPLOAD_DRAFT
                return (
                  <article key={item.id} className="timeline-item">
                    <p>
                      <strong>{item.title}</strong>
                    </p>
                    <p>Type: {item.request_type}</p>
                    <p>
                      Status: <span className={`status-tag ${item.status}`}>{item.status}</span>
                    </p>
                    <p>Doctor: {item.doctor_email || 'N/A'}</p>
                    <p>{item.description || 'No additional description.'}</p>
                    {(item.requested_items || []).length > 0 ? (
                      <p className="muted">Requested items: {(item.requested_items || []).join(', ')}</p>
                    ) : null}

                    {['pending', 'uploaded'].includes(item.status) ? (
                      <div className="form-grid">
                        <label>
                          Document type
                          <select
                            value={draft.document_type}
                            onChange={(event) =>
                              setUploadDrafts((prev) => ({
                                ...prev,
                                [uploadKey]: {
                                  ...draft,
                                  document_type: event.target.value,
                                },
                              }))
                            }
                          >
                            <option value="analysis_report">Analysis report</option>
                            <option value="imaging_result">Imaging result</option>
                            <option value="administrative">Administrative</option>
                            <option value="other">Other</option>
                          </select>
                        </label>

                        <label>
                          Title
                          <input
                            value={draft.title}
                            onChange={(event) =>
                              setUploadDrafts((prev) => ({
                                ...prev,
                                [uploadKey]: {
                                  ...draft,
                                  title: event.target.value,
                                },
                              }))
                            }
                            placeholder="Document title"
                          />
                        </label>

                        <label>
                          Notes (optional)
                          <textarea
                            value={draft.notes}
                            onChange={(event) =>
                              setUploadDrafts((prev) => ({
                                ...prev,
                                [uploadKey]: {
                                  ...draft,
                                  notes: event.target.value,
                                },
                              }))
                            }
                            placeholder="Optional comment for doctor"
                          />
                        </label>

                        <label>
                          File
                          <input
                            type="file"
                            onChange={(event) => {
                              const selectedFile = event.target.files?.[0] || null
                              setUploadDrafts((prev) => ({
                                ...prev,
                                [uploadKey]: {
                                  ...draft,
                                  file: selectedFile,
                                },
                              }))
                            }}
                          />
                        </label>

                        <button
                          type="button"
                          onClick={() => handleUploadForRequest(record.id, item.id)}
                          disabled={uploadMutation.isPending}
                        >
                          Upload requested document
                        </button>
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>

            <div className="timeline">
              <h4>Uploaded annexes and documents</h4>
              {(documentsByRecordId[record.id] || []).length === 0 ? (
                <p className="muted">No uploaded document for this record yet.</p>
              ) : null}

              {(documentsByRecordId[record.id] || []).map((document) => (
                <article key={document.id} className="timeline-item">
                  <p>
                    <strong>{document.title}</strong>
                  </p>
                  <p>Type: {document.document_type}</p>
                  <p>
                    Review status:{' '}
                    <span className={`status-tag ${document.review_status}`}>{document.review_status}</span>
                  </p>
                  <p>Uploaded at: {new Date(document.uploaded_at).toLocaleString()}</p>
                  {document.review_note ? <p className="muted">Doctor note: {document.review_note}</p> : null}
                  {document.file_url || document.file ? (
                    <a
                      href={resolveFileUrl(document.file_url || document.file)}
                      target="_blank"
                      rel="noreferrer"
                      className="primary-link"
                    >
                      Open file
                    </a>
                  ) : null}
                </article>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="card">
        <h3>Consultations</h3>
        {consultations.length === 0 ? <p className="muted">No consultations found.</p> : null}
        {consultations.map((consultation) => (
          <article key={consultation.id} className="timeline-item">
            <p>Diagnosis: {consultation.diagnosis}</p>
            <p>ICD10: {consultation.icd10_code || 'N/A'}</p>
            <p>Anamnesis: {consultation.anamnesis || 'N/A'}</p>
          </article>
        ))}
      </section>
    </div>
  )
}

export default MedicalRecordPage
