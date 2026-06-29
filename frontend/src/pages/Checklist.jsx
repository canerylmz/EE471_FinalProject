import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { exportChecklist, generateChecklist, getDut, getTest } from '../api'
import Spinner from '../components/Spinner'
import { downloadFromResponse } from '../utils/download'

const SECTION_DEFS = [
  { key: 'equipment_calibration', title: '1. Equipment & Calibration' },
  { key: 'safety_precautions', title: '2. Safety Precautions' },
  { key: 'dut_preparation', title: '3. DUT Preparation Steps' },
]

const toItems = (rawItems) =>
  (rawItems || []).map((item) => ({
    text: typeof item === 'string' ? item : item.text,
    checked: false,
    notes: '',
  }))

const today = () => new Date().toISOString().slice(0, 10)

export default function Checklist() {
  const { dutId, testId } = useParams()
  const navigate = useNavigate()

  const [dut, setDut] = useState(null)
  const [test, setTest] = useState(null)
  const [sections, setSections] = useState(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [engineerName, setEngineerName] = useState('')
  const [date, setDate] = useState(today())

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dutId, testId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [dutData, testData] = await Promise.all([getDut(dutId), getTest(testId)])
      setDut(dutData)
      setTest(testData)

      const checklistData = await generateChecklist(dutId, testId)
      setSections({
        equipment_calibration: toItems(checklistData.checklist.equipment_calibration),
        safety_precautions: toItems(checklistData.checklist.safety_precautions),
        dut_preparation: toItems(checklistData.checklist.dut_preparation),
      })

      if (checklistData.source === 'fallback') {
        toast('Ollama is unavailable, fallback checklist is shown.', { icon: '!' })
      } else {
        toast.success('Checklist generated.')
      }
    } catch (err) {
      toast.error(err.message || 'Checklist could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  const allChecked = useMemo(() => {
    if (!sections) return false
    return Object.values(sections).every((items) => items.every((item) => item.checked))
  }, [sections])

  const totalItems = useMemo(() => {
    if (!sections) return 0
    return Object.values(sections).reduce((sum, items) => sum + items.length, 0)
  }, [sections])

  const checkedItems = useMemo(() => {
    if (!sections) return 0
    return Object.values(sections).reduce(
      (sum, items) => sum + items.filter((item) => item.checked).length,
      0,
    )
  }, [sections])

  const toggleItem = (sectionKey, index) => {
    setSections((prev) => ({
      ...prev,
      [sectionKey]: prev[sectionKey].map((item, idx) =>
        idx === index ? { ...item, checked: !item.checked } : item,
      ),
    }))
  }

  const updateNotes = (sectionKey, index, value) => {
    setSections((prev) => ({
      ...prev,
      [sectionKey]: prev[sectionKey].map((item, idx) =>
        idx === index ? { ...item, notes: value } : item,
      ),
    }))
  }

  const handleExportPdf = async () => {
    setExporting(true)
    const toastId = toast.loading('Downloading checklist PDF...')
    try {
      const checklistData = {
        dut_name: dut?.name,
        test_name: test?.test_name,
        standard_reference: test?.standard_reference,
        engineer_name: engineerName,
        date,
        sections,
      }
      const response = await exportChecklist(checklistData)
      downloadFromResponse(response, `Checklist_${test?.test_name || testId}.pdf`)
      toast.success('Checklist PDF downloaded.', { id: toastId })
    } catch (err) {
      toast.error(err.message || 'PDF could not be downloaded.', { id: toastId })
    } finally {
      setExporting(false)
    }
  }

  const handleStartTest = () => {
    navigate(`/result/${dutId}/${testId}`)
  }

  if (loading) {
    return <Spinner size="lg" label="Generating checklist with Ollama..." />
  }

  if (!dut || !test || !sections) {
    return (
      <div className="card text-center text-slate-300">
        <p>Checklist could not be loaded.</p>
        <Link to={`/plan/${dutId}`} className="btn-primary mt-4 inline-flex">
          Back to Test Plan
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="card">
        <Link to={`/plan/${dutId}`} className="text-xs text-amber hover:underline">
          Back to Test Plan
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-100">{test.test_name}</h1>
        <p className="mt-1 text-sm text-slate-400">
          {test.standard_reference} - {dut.name}
        </p>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-navy">
          <div
            className="h-full rounded-full bg-amber transition-all"
            style={{ width: `${totalItems ? (checkedItems / totalItems) * 100 : 0}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {checkedItems} / {totalItems} items completed
        </p>
      </div>

      {SECTION_DEFS.map(({ key, title }) => (
        <div key={key} className="card">
          <h2 className="mb-3 text-lg font-semibold text-amber">{title}</h2>
          <div className="space-y-3">
            {sections[key].map((item, idx) => (
              <div key={idx} className="rounded-lg border border-slate-700 p-3">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-slate-500 bg-navy text-amber focus:ring-amber"
                    checked={item.checked}
                    onChange={() => toggleItem(key, idx)}
                  />
                  <span className="text-sm text-slate-200">{item.text}</span>
                </label>
                <input
                  type="text"
                  className="input-field mt-2 text-sm"
                  placeholder="Add note (optional)"
                  value={item.notes}
                  onChange={(e) => updateNotes(key, idx, e.target.value)}
                />
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="card">
        <h2 className="mb-3 text-lg font-semibold text-amber">Approval</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="label-field" htmlFor="engineer_name">
              Engineer Name
            </label>
            <input
              id="engineer_name"
              className="input-field"
              value={engineerName}
              onChange={(e) => setEngineerName(e.target.value)}
              placeholder="Full name"
            />
          </div>
          <div>
            <label className="label-field" htmlFor="checklist_date">
              Date
            </label>
            <input
              id="checklist_date"
              type="date"
              className="input-field"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-700 pt-4">
          <button
            type="button"
            className="btn-secondary"
            onClick={handleExportPdf}
            disabled={exporting}
          >
            {exporting && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-amber border-t-transparent" />
            )}
            {exporting ? 'Downloading...' : 'Download PDF'}
          </button>
          <button
            type="button"
            className="btn-primary flex-1"
            onClick={handleStartTest}
            disabled={!allChecked}
            title={!allChecked ? 'Check all items before continuing' : ''}
          >
            Complete and Start Test
          </button>
        </div>
      </div>
    </div>
  )
}
