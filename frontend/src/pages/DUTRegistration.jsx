import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { createDut, deleteDut, listDuts } from '../api'

const MOUNTING_LOCATIONS = [
  'Engine compartment',
  'Passenger compartment',
  'Exterior',
  'Underbody',
]

const POWER_CLASSES = ['Class I', 'Class II', 'Class III']
const NOMINAL_VOLTAGES = ['12V', '24V', '48V']

const initialState = {
  name: '',
  manufacturer: '',
  part_number: '',
  mounting_location: MOUNTING_LOCATIONS[0],
  power_class: POWER_CLASSES[0],
  nominal_voltage: NOMINAL_VOLTAGES[0],
  customer: '',
  project: '',
  temp_min: -40,
  temp_max: 85,
  ip_class: '',
  notes: '',
}

export default function DUTRegistration() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialState)
  const [duts, setDuts] = useState([])
  const [loadingDuts, setLoadingDuts] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadDuts()
  }, [])

  const loadDuts = async () => {
    setLoadingDuts(true)
    try {
      setDuts(await listDuts())
    } catch (err) {
      toast.error(err.message || 'DUT list could not be loaded.')
    } finally {
      setLoadingDuts(false)
    }
  }

  const handleChange = (event) => {
    const { name, value, type } = event.target
    setForm((prev) => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!form.name.trim()) {
      toast.error('DUT name is required.')
      return
    }
    if (Number(form.temp_min) > Number(form.temp_max)) {
      toast.error('Minimum operating temperature cannot be greater than maximum temperature.')
      return
    }

    setSubmitting(true)
    try {
      const dut = await createDut(form)
      toast.success('DUT saved successfully.')
      await loadDuts()
      navigate(`/plan/${dut.id}`)
    } catch (err) {
      toast.error(err.message || 'DUT could not be saved.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (dut) => {
    const label = dut.project ? `${dut.name} / ${dut.project}` : dut.name
    if (!window.confirm(`Delete ${label} and all related tests, results, attachments, and plan items?`)) {
      return
    }
    setDeletingId(dut.id)
    try {
      await deleteDut(dut.id)
      toast.success('DUT and related project data deleted.')
      await loadDuts()
    } catch (err) {
      toast.error(err.message || 'DUT could not be deleted.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">DUT Registration</h1>
        <p className="mt-1 text-sm text-slate-400">
          Register device-under-test information used for AI-assisted ISO 16750 test planning.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-6">
        <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <legend className="col-span-full mb-1 text-sm font-semibold text-amber">
            General Information
          </legend>

          <TextInput label="DUT Name *" name="name" value={form.name} onChange={handleChange} placeholder="e.g. Body Control Module" required />
          <TextInput label="Manufacturer" name="manufacturer" value={form.manufacturer} onChange={handleChange} placeholder="e.g. Bosch" />
          <TextInput label="Part Number" name="part_number" value={form.part_number} onChange={handleChange} placeholder="e.g. BCM-12345-A" />
          <TextInput label="IP Code" name="ip_class" value={form.ip_class} onChange={handleChange} placeholder="e.g. IP67" />
        </fieldset>

        <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <legend className="col-span-full mb-1 text-sm font-semibold text-amber">
            Technical Characteristics
          </legend>

          <SelectInput label="Mounting Location" name="mounting_location" value={form.mounting_location} options={MOUNTING_LOCATIONS} onChange={handleChange} />
          <SelectInput label="Power Class" name="power_class" value={form.power_class} options={POWER_CLASSES} onChange={handleChange} />
          <SelectInput label="Nominal Voltage" name="nominal_voltage" value={form.nominal_voltage} options={NOMINAL_VOLTAGES} onChange={handleChange} />
          <NumberInput label="Min. Operating Temperature (C)" name="temp_min" value={form.temp_min} onChange={handleChange} />
          <NumberInput label="Max. Operating Temperature (C)" name="temp_max" value={form.temp_max} onChange={handleChange} />
        </fieldset>

        <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <legend className="col-span-full mb-1 text-sm font-semibold text-amber">
            Project Information
          </legend>

          <TextInput label="Client Name" name="customer" value={form.customer} onChange={handleChange} placeholder="e.g. ACME Automotive" />
          <TextInput label="Project Name" name="project" value={form.project} onChange={handleChange} placeholder="e.g. Project X" />
        </fieldset>

        <div>
          <label className="label-field" htmlFor="notes">
            Notes
          </label>
          <textarea
            id="notes"
            name="notes"
            rows={4}
            className="input-field"
            value={form.notes}
            onChange={handleChange}
            placeholder="Additional information..."
          />
        </div>

        <div className="flex justify-end border-t border-slate-700 pt-4">
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy border-t-transparent" />
            )}
            {submitting ? 'Saving...' : 'Save and Generate Test Plan'}
          </button>
        </div>
      </form>

      <div className="card overflow-x-auto">
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-amber">Registered DUTs / Projects</h2>
          <p className="mt-1 text-sm text-slate-400">
            Open an existing test plan or delete a DUT with its related workflow data.
          </p>
        </div>
        <table className="min-w-full divide-y divide-slate-700 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-3 py-2">DUT</th>
              <th className="px-3 py-2">Project</th>
              <th className="px-3 py-2">Client</th>
              <th className="px-3 py-2">Part Number</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loadingDuts ? (
              <tr>
                <td className="px-3 py-4 text-slate-400" colSpan={5}>Loading DUT records...</td>
              </tr>
            ) : duts.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-slate-400" colSpan={5}>
                  No DUT records are available. Register a DUT above to start a project workflow.
                </td>
              </tr>
            ) : (
              duts.map((dut) => (
                <tr key={dut.id}>
                  <td className="px-3 py-2 font-medium text-slate-100">{dut.name}</td>
                  <td className="px-3 py-2 text-slate-300">{dut.project || '-'}</td>
                  <td className="px-3 py-2 text-slate-300">{dut.customer || '-'}</td>
                  <td className="px-3 py-2 text-slate-300">{dut.part_number || '-'}</td>
                  <td className="px-3 py-2 text-right">
                    <Link to={`/plan/${dut.id}`} className="mr-3 text-amber hover:underline">
                      Open Plan
                    </Link>
                    <button
                      type="button"
                      className="text-red-300 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={deletingId === dut.id}
                      onClick={() => handleDelete(dut)}
                    >
                      {deletingId === dut.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TextInput({ label, name, value, onChange, placeholder, required }) {
  return (
    <div>
      <label className="label-field" htmlFor={name}>{label}</label>
      <input id={name} name={name} className="input-field" value={value} onChange={onChange} placeholder={placeholder} required={required} />
    </div>
  )
}

function NumberInput({ label, name, value, onChange }) {
  return (
    <div>
      <label className="label-field" htmlFor={name}>{label}</label>
      <input id={name} name={name} type="number" className="input-field" value={value} onChange={onChange} />
    </div>
  )
}

function SelectInput({ label, name, value, options, onChange }) {
  return (
    <div>
      <label className="label-field" htmlFor={name}>{label}</label>
      <select id={name} name={name} className="input-field" value={value} onChange={onChange}>
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </div>
  )
}
