import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { createPrescription, getPrescriptionPdfUrl } from '../../api/prescriptionsApi'
import PrescriptionForm from '../../components/PrescriptionForm'

function PrescriptionPage() {
  const [pdfUrl, setPdfUrl] = useState('')

  const mutation = useMutation({
    mutationFn: createPrescription,
    onSuccess: (data) => {
      toast.success('Prescription saved')
      setPdfUrl(getPrescriptionPdfUrl(data.id))
    },
    onError: () => toast.error('Unable to save prescription'),
  })

  return (
    <div className="stacked-grid">
      <section className="card page-hero">
        <h2>Prescription Studio</h2>
        <p className="muted">Compose medication plans with real-time preview and instant PDF export.</p>
      </section>
      <PrescriptionForm onSubmit={(values) => mutation.mutate(values)} pdfUrl={pdfUrl} />
    </div>
  )
}

export default PrescriptionPage
