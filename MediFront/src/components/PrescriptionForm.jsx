import { useMemo } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'

const defaultValues = {
  consultation: '',
  doctor: '',
  patient: '',
  notes: '',
  items: [{ medication: '', dosage: '', frequency: '', duration: '', instructions: '' }],
}

function PrescriptionForm({ onSubmit, pdfUrl }) {
  const { register, control, handleSubmit, watch } = useForm({ defaultValues })
  const { fields, append, remove } = useFieldArray({ control, name: 'items' })
  const values = watch()

  const previewLines = useMemo(
    () =>
      values.items
        .filter((item) => item.medication)
        .map((item) => `${item.medication} - ${item.dosage} - ${item.frequency} - ${item.duration}`),
    [values.items],
  )

  return (
    <div className="split-grid">
      <section className="card">
        <h3>Create Prescription</h3>
        <p className="muted">Fill identifiers, then add medication lines with dosage and duration.</p>
        <form className="form-grid" onSubmit={handleSubmit(onSubmit)}>
          <input placeholder="Consultation ID" {...register('consultation')} />
          <input placeholder="Doctor Profile ID" {...register('doctor')} />
          <input placeholder="Patient Profile ID" {...register('patient')} />
          <textarea placeholder="Notes" {...register('notes')} />

          <h4>Medications</h4>
          {fields.map((field, index) => (
            <div key={field.id} className="item-row">
              <input placeholder="Medication" {...register(`items.${index}.medication`)} />
              <input placeholder="Dosage" {...register(`items.${index}.dosage`)} />
              <input placeholder="Frequency" {...register(`items.${index}.frequency`)} />
              <input placeholder="Duration" {...register(`items.${index}.duration`)} />
              <input placeholder="Instructions" {...register(`items.${index}.instructions`)} />
              <button className="secondary-btn" type="button" onClick={() => remove(index)}>
                Remove
              </button>
            </div>
          ))}

          <button
            className="ghost-btn"
            type="button"
            onClick={() => append({ medication: '', dosage: '', frequency: '', duration: '', instructions: '' })}
          >
            Add Medication
          </button>
          <button type="submit">Save Prescription</button>
        </form>
      </section>

      <section className="card">
        <h3>Live Preview</h3>
        <p className="muted">This preview helps validate medications before generating the PDF.</p>
        <ul>
          {previewLines.length === 0 ? <li>No medications yet.</li> : null}
          {previewLines.map((line, idx) => (
            <li key={`${line}-${idx}`}>{line}</li>
          ))}
        </ul>
        {pdfUrl ? (
          <a className="primary-link" href={pdfUrl} target="_blank" rel="noreferrer">
            Open PDF
          </a>
        ) : null}
      </section>
    </div>
  )
}

export default PrescriptionForm
