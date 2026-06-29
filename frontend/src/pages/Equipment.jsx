import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { createEquipment, deleteEquipment, listEquipment, updateEquipment } from '../api'
import Spinner from '../components/Spinner'

const emptyForm = {
  equipment_no: '',
  kind_of_equipment: '',
  model: '',
  type: '',
  manufacturer: '',
  serial_no: '',
  last_calibration_date: '',
  next_calibration_date: '',
  last_verification_date: '',
  next_verification_date: '',
  using_status: 'available',
  location: '',
  notes: '',
}

export default function Equipment() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    setLoading(true)
    try {
      const data = await listEquipment()
      setItems(data.equipment || [])
    } catch (err) {
      toast.error(err.message || 'Equipment could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    try {
      if (editingId) {
        await updateEquipment(editingId, form)
        toast.success('Equipment updated.')
      } else {
        await createEquipment(form)
        toast.success('Equipment created.')
      }
      setForm(emptyForm)
      setEditingId(null)
      await load()
    } catch (err) {
      toast.error(err.message || 'Equipment could not be saved.')
    }
  }

  const edit = (item) => {
    setEditingId(item.id)
    setForm({ ...emptyForm, ...item })
  }

  const remove = async (id) => {
    try {
      await deleteEquipment(id)
      toast.success('Equipment deleted.')
      await load()
    } catch (err) {
      toast.error(err.message || 'Equipment could not be deleted.')
    }
  }

  if (loading) return <Spinner size="lg" label="Loading equipment..." />

  const expiredCount = items.filter((item) => item.calibration_status === 'expired').length
  const dueSoonCount = items.filter((item) => item.calibration_status === 'due_soon').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Equipment</h1>
        <p className="mt-1 text-sm text-slate-400">
          Manage laboratory equipment and calibration status used during testing.
        </p>
        {(expiredCount > 0 || dueSoonCount > 0) && (
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            {expiredCount > 0 && (
              <span className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-red-300">
                {expiredCount} expired calibration record{expiredCount === 1 ? '' : 's'}
              </span>
            )}
            {dueSoonCount > 0 && (
              <span className="rounded-md border border-amber/40 bg-amber/10 px-3 py-2 text-amber">
                {dueSoonCount} calibration record{dueSoonCount === 1 ? '' : 's'} due soon
              </span>
            )}
          </div>
        )}
      </div>
      <form onSubmit={submit} className="card grid grid-cols-1 gap-4 md:grid-cols-3">
        <TextField label="Equipment No" name="equipment_no" form={form} setForm={setForm} />
        <TextField label="Kind of Equipment" name="kind_of_equipment" form={form} setForm={setForm} />
        <TextField label="Model" name="model" form={form} setForm={setForm} />
        <TextField label="Type" name="type" form={form} setForm={setForm} />
        <TextField label="Manufacturer" name="manufacturer" form={form} setForm={setForm} />
        <TextField label="Serial No" name="serial_no" form={form} setForm={setForm} />
        <DateField label="Last Calibration Date" name="last_calibration_date" form={form} setForm={setForm} />
        <DateField label="Next Calibration Date" name="next_calibration_date" form={form} setForm={setForm} />
        <DateField label="Last Verification Date" name="last_verification_date" form={form} setForm={setForm} />
        <DateField label="Next Verification Date" name="next_verification_date" form={form} setForm={setForm} />
        <TextField label="Using Status" name="using_status" form={form} setForm={setForm} />
        <TextField label="Location" name="location" form={form} setForm={setForm} />
        <div className="md:col-span-3">
          <TextField label="Notes" name="notes" form={form} setForm={setForm} />
        </div>
        <div className="md:col-span-3 flex gap-2">
          <button type="submit" className="btn-primary">
            {editingId ? 'Update Equipment' : 'Create Equipment'}
          </button>
          {editingId && (
            <button type="button" className="btn-secondary" onClick={() => { setEditingId(null); setForm(emptyForm) }}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-700 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-3 py-2">Equipment No</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Model</th>
              <th className="px-3 py-2">Next Calibration</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {items.map((item) => (
              <tr key={item.id}>
                <td className="px-3 py-2 text-slate-200">{item.equipment_no || '-'}</td>
                <td className="px-3 py-2 text-slate-300">{item.kind_of_equipment || '-'}</td>
                <td className="px-3 py-2 text-slate-300">{item.model || '-'}</td>
                <td className="px-3 py-2 text-slate-300">{item.next_calibration_date || '-'}</td>
                <td className="px-3 py-2"><CalibrationBadge status={item.calibration_status} /></td>
                <td className="px-3 py-2 text-right">
                  <button type="button" className="mr-3 text-amber hover:underline" onClick={() => edit(item)}>Edit</button>
                  <button type="button" className="text-red-300 hover:underline" onClick={() => remove(item.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td className="px-3 py-8 text-center text-slate-400" colSpan={6}>
                  No equipment records are available yet. Create equipment here, then link it from a Result Report page.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TextField({ label, name, form, setForm }) {
  return (
    <div>
      <label className="label-field" htmlFor={name}>{label}</label>
      <input id={name} className="input-field" value={form[name] || ''} onChange={(e) => setForm((prev) => ({ ...prev, [name]: e.target.value }))} />
    </div>
  )
}

function DateField(props) {
  return <TextField {...props} />
}

export function CalibrationBadge({ status }) {
  const styles = {
    valid: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
    due_soon: 'bg-amber/20 text-amber border border-amber/40',
    expired: 'bg-red-500/20 text-red-300 border border-red-500/40',
    not_available: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
  }
  const labels = {
    valid: 'Valid',
    due_soon: 'Due Soon',
    expired: 'Expired',
    not_available: 'Not Available',
  }
  return <span className={`badge ${styles[status] || styles.not_available}`}>{labels[status] || labels.not_available}</span>
}
