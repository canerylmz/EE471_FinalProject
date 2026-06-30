import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  deleteAttachment,
  downloadAttachment,
  exportReportDocx,
  exportReportPdf,
  generateReport,
  generateTestRecordForm,
  getDut,
  getResult,
  getResultSchema,
  getTest,
  linkEquipmentToTest,
  listEquipment,
  listTestEquipment,
  listTestAttachments,
  saveResult,
  unlinkEquipment,
  uploadAttachment,
} from '../api'
import Spinner from '../components/Spinner'
import { downloadFromResponse } from '../utils/download'

const REPORT_SECTION_TITLES = {
  test_amaci: '1. Test Purpose',
  test_kosullari: '2. Test Conditions',
  olcum_sonuclari: '3. Measurement Results',
  gozlemler: '4. Observations',
  kabul_degerlendirme: '5. Acceptance Criteria Evaluation',
  sonuc: '6. Result and Decision',
  sapma_analizi: '7. Deviation Analysis and Corrective Action',
}

const ATTACHMENT_TYPES = [
  { value: 'test_photo', label: 'Test Photo' },
  { value: 'measurement_file', label: 'Measurement File' },
  { value: 'temperature_humidity_log', label: 'Temperature-Humidity Log' },
  { value: 'calibration_certificate', label: 'Calibration Certificate' },
  { value: 'raw_data', label: 'Raw Data' },
  { value: 'test_record_form', label: 'Test Record Form' },
  { value: 'supporting_document', label: 'Supporting Document' },
]

const EVALUATION_LABEL_OVERRIDES = {
  ac_voltage_upp: 'AC Voltage UPP',
  functional_observation: 'Functional Observation',
  functional_status_review: 'Functional Status Review',
  max: 'Maximum',
  min: 'Minimum',
  number_of_sweeps: 'Number of Sweeps',
  range: 'Range',
  test_voltage: 'Test Voltage',
}

const formatEvaluationLabel = (value) => {
  if (!value) return 'General'
  if (EVALUATION_LABEL_OVERRIDES[value]) return EVALUATION_LABEL_OVERRIDES[value]

  return String(value)
    .split('_')
    .filter(Boolean)
    .map((word) => {
      const upperWord = word.toUpperCase()
      if (['AC', 'DC', 'DUT', 'ISO', 'UPP'].includes(upperWord)) return upperWord
      return `${word.charAt(0).toUpperCase()}${word.slice(1)}`
    })
    .join(' ')
}

export default function ResultReport() {
  const { dutId, testId } = useParams()

  const [dut, setDut] = useState(null)
  const [test, setTest] = useState(null)
  const [resultSchema, setResultSchema] = useState([])
  const [schemaMetadata, setSchemaMetadata] = useState({})
  const [evaluationSchema, setEvaluationSchema] = useState({})
  const [loading, setLoading] = useState(true)

  const [result, setResult] = useState('NOT EVALUATED')
  const [evaluation, setEvaluation] = useState({
    status: 'NOT EVALUATED',
    score: null,
    failed_rules: [],
    evaluation_details: [],
  })
  const [measuredValues, setMeasuredValues] = useState({})
  const [temperature, setTemperature] = useState('')
  const [humidity, setHumidity] = useState('')
  const [observations, setObservations] = useState('')
  const [hasDeviation, setHasDeviation] = useState(false)
  const [deviationDescription, setDeviationDescription] = useState('')
  const [rootCause, setRootCause] = useState('')
  const [correctiveAction, setCorrectiveAction] = useState('')
  const [engineerName, setEngineerName] = useState('')

  const [saving, setSaving] = useState(false)
  const [report, setReport] = useState(null)
  const [exportingDocx, setExportingDocx] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [generatingRecordForm, setGeneratingRecordForm] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [attachmentType, setAttachmentType] = useState('test_photo')
  const [attachmentDescription, setAttachmentDescription] = useState('')
  const [attachmentFile, setAttachmentFile] = useState(null)
  const [uploadingAttachment, setUploadingAttachment] = useState(false)
  const [equipment, setEquipment] = useState([])
  const [linkedEquipment, setLinkedEquipment] = useState([])
  const [selectedEquipmentId, setSelectedEquipmentId] = useState('')
  const [equipmentUsageRole, setEquipmentUsageRole] = useState('')
  const [linkingEquipment, setLinkingEquipment] = useState(false)

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dutId, testId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [dutData, testData, schemaData] = await Promise.all([
        getDut(dutId),
        getTest(testId),
        getResultSchema(testId),
      ])
      setDut(dutData)
      setTest(testData)
      setResultSchema(schemaData.schema || [])
      setSchemaMetadata(schemaData.test || {})
      setEvaluationSchema(schemaData.evaluation_schema || {})
      await loadAttachments()
      await loadEquipment()

      try {
        const existing = await getResult(testId)
        applyExistingResult(existing)
      } catch {
        // No existing result yet.
      }
    } catch (err) {
      toast.error(err.message || 'Data could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  const loadAttachments = async () => {
    try {
      const data = await listTestAttachments(testId)
      setAttachments(data.attachments || [])
    } catch (err) {
      toast.error(err.message || 'Attachments could not be loaded.')
    }
  }

  const loadEquipment = async () => {
    try {
      const [equipmentData, linkedData] = await Promise.all([
        listEquipment(),
        listTestEquipment(testId),
      ])
      setEquipment(equipmentData.equipment || [])
      setLinkedEquipment(linkedData.equipment || [])
    } catch (err) {
      toast.error(err.message || 'Equipment could not be loaded.')
    }
  }

  const applyExistingResult = (existing) => {
    setResult(existing.result || 'Pass')
    setEvaluation(
      existing.evaluation_details || {
        status: existing.evaluation_status || 'NOT EVALUATED',
        score: existing.evaluation_score ?? null,
        failed_rules: [],
        evaluation_details: [],
      },
    )
    setMeasuredValues(existing.measured_values || {})
    setTemperature(existing.temp ?? '')
    setHumidity(existing.humidity ?? '')
    setObservations(existing.observations || '')
    setHasDeviation(Boolean(existing.has_deviation))
    setDeviationDescription(existing.deviation_description || '')
    setRootCause(existing.root_cause || '')
    setCorrectiveAction(existing.corrective_action || '')
    setEngineerName(existing.engineer_name || '')
    if (existing.report_text) {
      setReport(existing.report_text)
    }
  }

  const updateMeasuredValue = (name, value, type) => {
    setMeasuredValues((prev) => ({
      ...prev,
      [name]: type === 'number' && value !== '' ? Number(value) : value,
    }))
  }

  const buildResultData = () => ({
    result,
    measured_values: measuredValues,
    test_conditions: {
      temperature: temperature === '' ? null : Number(temperature),
      humidity: humidity === '' ? null : Number(humidity),
    },
    observations,
    has_deviation: hasDeviation,
    deviation_description: hasDeviation ? deviationDescription : '',
    root_cause: hasDeviation ? rootCause : '',
    corrective_action: hasDeviation ? correctiveAction : '',
    engineer_name: engineerName,
  })

  const handleGenerateReport = async (event) => {
    event.preventDefault()
    setSaving(true)
    setReport(null)
    try {
      const resultData = buildResultData()
      const saved = await saveResult({
        test_id: Number(testId),
        dut_id: Number(dutId),
        ...resultData,
      })
      const savedEvaluation = saved.evaluation_details || {
        status: saved.evaluation_status || 'NOT EVALUATED',
        score: saved.evaluation_score ?? null,
        failed_rules: [],
        evaluation_details: [],
      }
      setEvaluation(savedEvaluation)
      setResult(saved.result || savedEvaluation.status)

      const reportResponse = await generateReport(dutId, testId, {
        ...resultData,
        result: saved.result || savedEvaluation.status,
      })
      setReport(reportResponse.report)

      if (reportResponse.source === 'fallback') {
        toast('Ollama is unavailable, fallback report text is shown.', { icon: '!' })
      } else {
        toast.success('Report generated by Ollama.')
      }
    } catch (err) {
      toast.error(err.message || 'Report could not be generated.')
    } finally {
      setSaving(false)
    }
  }

  const handleExportDocx = async () => {
    setExportingDocx(true)
    const toastId = toast.loading('Downloading DOCX report...')
    try {
      const response = await exportReportDocx(dutId, testId)
      downloadFromResponse(response, `TestReport_${test?.test_name || testId}.docx`)
      toast.success('DOCX report downloaded.', { id: toastId })
    } catch (err) {
      toast.error(err.message || 'DOCX could not be downloaded.', { id: toastId })
    } finally {
      setExportingDocx(false)
    }
  }

  const handleExportPdf = async () => {
    setExportingPdf(true)
    const toastId = toast.loading('Downloading PDF report...')
    try {
      const response = await exportReportPdf(dutId, testId)
      downloadFromResponse(response, `TestReport_${test?.test_name || testId}.pdf`)
      toast.success('PDF report downloaded.', { id: toastId })
    } catch (err) {
      toast.error(err.message || 'PDF could not be downloaded.', { id: toastId })
    } finally {
      setExportingPdf(false)
    }
  }

  const handleGenerateRecordForm = async () => {
    setGeneratingRecordForm(true)
    const toastId = toast.loading('Generating test record form...')
    try {
      const response = await generateTestRecordForm(testId)
      downloadFromResponse(response, `TestRecordForm_${test?.test_name || testId}.docx`)
      toast.success('Test record form downloaded.', { id: toastId })
    } catch (err) {
      toast.error(err.message || 'Test record form could not be generated.', { id: toastId })
    } finally {
      setGeneratingRecordForm(false)
    }
  }

  const handleUploadAttachment = async (event) => {
    event.preventDefault()
    if (!attachmentFile) {
      toast.error('Select a file to upload.')
      return
    }
    setUploadingAttachment(true)
    const formData = new FormData()
    formData.append('dut_id', dutId)
    formData.append('test_id', testId)
    formData.append('attachment_type', attachmentType)
    formData.append('description', attachmentDescription)
    formData.append('file', attachmentFile)
    try {
      await uploadAttachment(formData)
      toast.success('Attachment uploaded.')
      setAttachmentDescription('')
      setAttachmentFile(null)
      await loadAttachments()
    } catch (err) {
      toast.error(err.message || 'Attachment could not be uploaded.')
    } finally {
      setUploadingAttachment(false)
    }
  }

  const handleDownloadAttachment = async (attachment) => {
    try {
      const response = await downloadAttachment(attachment.id)
      downloadFromResponse(response, attachment.original_filename || attachment.file_name || 'attachment')
    } catch (err) {
      toast.error(err.message || 'Attachment could not be downloaded.')
    }
  }

  const handleDeleteAttachment = async (attachmentId) => {
    try {
      await deleteAttachment(attachmentId)
      toast.success('Attachment deleted.')
      await loadAttachments()
    } catch (err) {
      toast.error(err.message || 'Attachment could not be deleted.')
    }
  }

  const handleLinkEquipment = async (event) => {
    event.preventDefault()
    if (!selectedEquipmentId) {
      toast.error('Select equipment to link.')
      return
    }
    setLinkingEquipment(true)
    try {
      await linkEquipmentToTest(Number(testId), Number(selectedEquipmentId), equipmentUsageRole)
      toast.success('Equipment linked to test.')
      setSelectedEquipmentId('')
      setEquipmentUsageRole('')
      await loadEquipment()
    } catch (err) {
      toast.error(err.message || 'Equipment could not be linked.')
    } finally {
      setLinkingEquipment(false)
    }
  }

  const handleUnlinkEquipment = async (linkId) => {
    try {
      await unlinkEquipment(linkId)
      toast.success('Equipment unlinked from test.')
      await loadEquipment()
    } catch (err) {
      toast.error(err.message || 'Equipment could not be unlinked.')
    }
  }

  if (loading) {
    return <Spinner size="lg" label="Loading..." />
  }

  if (!dut || !test) {
    return (
      <div className="card text-center text-slate-300">
        <p>Test not found.</p>
        <Link to={`/plan/${dutId}`} className="btn-primary mt-4 inline-flex">
          Back to Test Plan
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="card">
        <Link to={`/plan/${dutId}`} className="text-xs text-amber hover:underline">
          Back to Test Plan
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-100">{test.test_name}</h1>
        <p className="mt-1 text-sm text-slate-400">
          {test.standard_reference} - {dut.name}
        </p>
        <p className="mt-2 text-sm text-slate-400">
          Enter measured values, review automatic evaluation, attach evidence, and generate documents.
        </p>
      </div>

      <form onSubmit={handleGenerateReport} className="card space-y-6">
        <RequiredParametersPanel
          metadata={schemaMetadata}
          schema={resultSchema}
          evaluationSchema={evaluationSchema}
        />

        <section>
          <h2 className="mb-3 text-lg font-semibold text-amber">Dynamic Measurements</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {resultSchema.length === 0 ? (
              <p className="text-sm text-slate-400 sm:col-span-2">
                No dynamic measurement fields are defined for this test. Use General Result Information for observations.
              </p>
            ) : resultSchema.map((field) => (
              <DynamicField
                key={field.name}
                field={field}
                value={measuredValues[field.name] ?? ''}
                onChange={updateMeasuredValue}
              />
            ))}
          </div>
        </section>

        <EvaluationPanel evaluation={evaluation} result={result} />

        <section>
          <h2 className="mb-3 text-lg font-semibold text-amber">General Result Information</h2>
          <p className="mb-4 text-sm text-slate-400">
            Record environmental conditions, observations, deviations, and operator information.
          </p>
          <p className="label-field">Test Conditions</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <NumberField label="Temperature (C)" value={temperature} onChange={setTemperature} />
            <NumberField label="Humidity (%)" value={humidity} onChange={setHumidity} />
          </div>
        </section>

        <div>
          <label className="label-field" htmlFor="observations">
            Observations
          </label>
          <textarea
            id="observations"
            rows={4}
            className="input-field"
            value={observations}
            onChange={(e) => setObservations(e.target.value)}
          />
        </div>

        <div>
          <label className="flex items-center gap-3">
            <span className="label-field mb-0">Applied Parameter Deviation?</span>
            <button
              type="button"
              role="switch"
              aria-checked={hasDeviation}
              onClick={() => setHasDeviation((prev) => !prev)}
              className={`relative h-6 w-11 rounded-full transition ${
                hasDeviation ? 'bg-amber' : 'bg-slate-600'
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                  hasDeviation ? 'left-5' : 'left-0.5'
                }`}
              />
            </button>
            <span className="text-sm text-slate-300">{hasDeviation ? 'Yes' : 'No'}</span>
          </label>
        </div>

        {hasDeviation && (
          <div className="space-y-4 rounded-lg border border-amber/30 bg-amber/5 p-4">
            <p className="text-sm text-slate-300">
              Use this section only when the applied test condition differs from the required value,
              such as a required 25.2 V test level that could only be applied as 25.0 V.
            </p>
            <TextAreaField
              label="Deviation Description"
              value={deviationDescription}
              onChange={setDeviationDescription}
            />
            <TextAreaField label="Reason for Applied Difference" value={rootCause} onChange={setRootCause} />
            <TextAreaField
              label="Approval / Technical Note"
              value={correctiveAction}
              onChange={setCorrectiveAction}
            />
          </div>
        )}

        <div>
          <label className="label-field" htmlFor="engineer_name">
            Engineer Name
          </label>
          <input
            id="engineer_name"
            className="input-field max-w-sm"
            value={engineerName}
            onChange={(e) => setEngineerName(e.target.value)}
          />
        </div>

        <div className="flex justify-end border-t border-slate-700 pt-4">
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy border-t-transparent" />
            )}
            {saving ? 'Generating Report...' : 'Generate Report'}
          </button>
        </div>
      </form>

      <EquipmentUsedPanel
        equipment={equipment}
        linkedEquipment={linkedEquipment}
        selectedEquipmentId={selectedEquipmentId}
        setSelectedEquipmentId={setSelectedEquipmentId}
        usageRole={equipmentUsageRole}
        setUsageRole={setEquipmentUsageRole}
        linking={linkingEquipment}
        onLink={handleLinkEquipment}
        onUnlink={handleUnlinkEquipment}
      />

      <AttachmentsPanel
        attachments={attachments}
        attachmentType={attachmentType}
        setAttachmentType={setAttachmentType}
        attachmentDescription={attachmentDescription}
        setAttachmentDescription={setAttachmentDescription}
        setAttachmentFile={setAttachmentFile}
        uploading={uploadingAttachment}
        onUpload={handleUploadAttachment}
        onDownload={handleDownloadAttachment}
        onDelete={handleDeleteAttachment}
      />

      <DocumentGenerationPanel
        report={report}
        exportingDocx={exportingDocx}
        exportingPdf={exportingPdf}
        generatingRecordForm={generatingRecordForm}
        onGenerateRecordForm={handleGenerateRecordForm}
        onExportDocx={handleExportDocx}
        onExportPdf={handleExportPdf}
      />

      {report && (
        <div className="card space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 pb-3">
            <h2 className="text-lg font-semibold text-amber">Report Preview</h2>
          </div>

          {Object.entries(REPORT_SECTION_TITLES).map(([key, title]) =>
            report.sections?.[key] ? (
              <div key={key}>
                <h3 className="mb-1 text-sm font-semibold text-slate-200">{title}</h3>
                <p className="whitespace-pre-line text-sm text-slate-400">
                  {report.sections[key]}
                </p>
              </div>
            ) : null,
          )}
        </div>
      )}
    </div>
  )
}

function DocumentGenerationPanel({
  report,
  exportingDocx,
  exportingPdf,
  generatingRecordForm,
  onGenerateRecordForm,
  onExportDocx,
  onExportPdf,
}) {
  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-amber">Document Generation</h2>
        <p className="mt-1 text-sm text-slate-400">
          Generate the structured test record form and export the saved report when available.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-primary"
          onClick={onGenerateRecordForm}
          disabled={generatingRecordForm}
        >
          {generatingRecordForm ? 'Generating Test Record Form...' : 'Generate Test Record Form'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={onExportDocx}
          disabled={exportingDocx || !report}
        >
          {exportingDocx ? 'Downloading...' : 'Download DOCX Report'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          onClick={onExportPdf}
          disabled={exportingPdf || !report}
        >
          {exportingPdf ? 'Downloading...' : 'Download PDF Report'}
        </button>
      </div>
      {!report && (
        <p className="text-sm text-slate-500">
          Generate and save the result report before downloading report exports.
        </p>
      )}
    </div>
  )
}

function AttachmentsPanel({
  attachments,
  attachmentType,
  setAttachmentType,
  attachmentDescription,
  setAttachmentDescription,
  setAttachmentFile,
  uploading,
  onUpload,
  onDownload,
  onDelete,
}) {
  const typeLabel = (value) =>
    ATTACHMENT_TYPES.find((type) => type.value === value)?.label || 'Supporting Document'

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-amber">Attachments</h2>
        <p className="mt-1 text-sm text-slate-400">
          Upload supporting files for this DUT and test.
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Uploaded attachments will be referenced in generated Test Record Forms and Technical Reports.
        </p>
      </div>

      <form onSubmit={onUpload} className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div>
          <label className="label-field" htmlFor="attachment_type">
            Attachment Type
          </label>
          <select
            id="attachment_type"
            className="input-field"
            value={attachmentType}
            onChange={(event) => setAttachmentType(event.target.value)}
          >
            {ATTACHMENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
        <div className="lg:col-span-2">
          <label className="label-field" htmlFor="attachment_description">
            Description
          </label>
          <input
            id="attachment_description"
            className="input-field"
            value={attachmentDescription}
            onChange={(event) => setAttachmentDescription(event.target.value)}
            placeholder="Optional description"
          />
        </div>
        <div>
          <label className="label-field" htmlFor="attachment_file">
            File
          </label>
          <input
            id="attachment_file"
            type="file"
            className="input-field"
            onChange={(event) => setAttachmentFile(event.target.files?.[0] || null)}
          />
        </div>
        <div className="lg:col-span-4">
          <button type="submit" className="btn-secondary" disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload Attachment'}
          </button>
        </div>
      </form>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-700 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-3 py-2">Type</th>
              <th className="px-3 py-2">File</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Size</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {attachments.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-slate-400" colSpan={5}>
                  No attachments uploaded yet. Upload photos, measurement files, or supporting evidence after saving the result.
                </td>
              </tr>
            ) : (
              attachments.map((attachment) => (
                <tr key={attachment.id}>
                  <td className="px-3 py-2 text-slate-300">
                    {typeLabel(attachment.attachment_type)}
                  </td>
                  <td className="px-3 py-2 text-slate-200">
                    {attachment.original_filename || attachment.file_name}
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    {attachment.description || '-'}
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    {formatBytes(attachment.file_size)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      className="mr-3 text-amber hover:underline"
                      onClick={() => onDownload(attachment)}
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      className="text-red-300 hover:underline"
                      onClick={() => onDelete(attachment.id)}
                    >
                      Delete
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

function formatBytes(value) {
  if (!value) return '-'
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${Math.round((value / (1024 * 1024)) * 10) / 10} MB`
}

function EquipmentUsedPanel({
  equipment,
  linkedEquipment,
  selectedEquipmentId,
  setSelectedEquipmentId,
  usageRole,
  setUsageRole,
  linking,
  onLink,
  onUnlink,
}) {
  const linkedIds = new Set(linkedEquipment.map((item) => item.id))
  const availableEquipment = equipment.filter((item) => !linkedIds.has(item.id))
  const hasExpired = linkedEquipment.some((item) => item.calibration_status === 'expired')

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-amber">Equipment Used</h2>
        <p className="mt-1 text-sm text-slate-400">
          Link calibrated laboratory equipment used during this test.
        </p>
        {hasExpired && (
          <p className="mt-2 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            Warning: expired equipment is linked to this test.
          </p>
        )}
      </div>

      <form onSubmit={onLink} className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="lg:col-span-2">
          <label className="label-field" htmlFor="equipment_select">
            Equipment
          </label>
          <select
            id="equipment_select"
            className="input-field"
            value={selectedEquipmentId}
            onChange={(event) => setSelectedEquipmentId(event.target.value)}
          >
            <option value="">Select equipment...</option>
            {availableEquipment.map((item) => (
              <option key={item.id} value={item.id}>
                {equipmentLabel(item)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label-field" htmlFor="usage_role">
            Usage Role
          </label>
          <input
            id="usage_role"
            className="input-field"
            value={usageRole}
            onChange={(event) => setUsageRole(event.target.value)}
            placeholder="e.g. Power supply"
          />
        </div>
        <div className="flex items-end">
          <button type="submit" className="btn-secondary w-full" disabled={linking}>
            {linking ? 'Linking...' : 'Link Equipment'}
          </button>
        </div>
      </form>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-700 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-3 py-2">Equipment No</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Usage Role</th>
              <th className="px-3 py-2">Next Calibration</th>
              <th className="px-3 py-2">Calibration Status</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {linkedEquipment.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-slate-400" colSpan={6}>
                  No equipment linked to this test yet. Select calibrated equipment above to include it in generated documents.
                </td>
              </tr>
            ) : (
              linkedEquipment.map((item) => (
                <tr key={item.link_id}>
                  <td className="px-3 py-2 text-slate-200">{item.equipment_no || '-'}</td>
                  <td className="px-3 py-2 text-slate-300">{item.kind_of_equipment || '-'}</td>
                  <td className="px-3 py-2 text-slate-300">{item.usage_role || '-'}</td>
                  <td className="px-3 py-2 text-slate-300">{item.next_calibration_date || '-'}</td>
                  <td className="px-3 py-2">
                    <CalibrationBadge status={item.calibration_status} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      className="text-red-300 hover:underline"
                      onClick={() => onUnlink(item.link_id)}
                    >
                      Unlink
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

function equipmentLabel(item) {
  return [item.equipment_no, item.kind_of_equipment, item.model].filter(Boolean).join(' - ') || `Equipment ${item.id}`
}

function CalibrationBadge({ status }) {
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

function RequiredParametersPanel({ metadata, schema, evaluationSchema }) {
  const rules = Array.isArray(evaluationSchema?.rules) ? evaluationSchema.rules : []
  const rows = [
    ['ISO Part', metadata?.iso_part],
    ['Clause No.', metadata?.clause_no],
    ['Test Name', metadata?.test_name],
    ['Operating Mode', metadata?.operating_mode],
    ['Required Test Level', metadata?.required_test_level],
    ['Required Functional Status', metadata?.functional_status],
    ['Severity', metadata?.severity],
    ['Sample Size', metadata?.sample_size],
  ]

  return (
    <section className="rounded-lg border border-slate-700 bg-navy/40 p-4">
      <h2 className="mb-3 text-lg font-semibold text-amber">Required Test Parameters</h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-md border border-slate-700 p-3">
            <p className="text-xs uppercase text-slate-500">{label}</p>
            <p className="mt-1 text-sm font-medium text-slate-200">{value || 'Not specified'}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-700 text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-3 py-2">Parameter</th>
              <th className="px-3 py-2">Required / Target Value</th>
              <th className="px-3 py-2">Rule / Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {(schema || []).map((field) => {
              const rule = rules.find((item) => item.field === field.name)
              return (
                <tr key={field.name}>
                  <td className="px-3 py-2 text-slate-200">
                    {field.label || field.name}
                    {field.unit ? ` (${field.unit})` : ''}
                    {field.required ? <span className="text-amber"> *</span> : null}
                  </td>
                  <td className="px-3 py-2 text-slate-300">{describeRequirement(rule, field)}</td>
                  <td className="px-3 py-2 text-slate-400">{describeRule(rule)}</td>
                </tr>
              )
            })}
            {(!schema || schema.length === 0) && (
              <tr>
                <td className="px-3 py-2 text-slate-400" colSpan={3}>
                  No dynamic parameter schema is defined for this test.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function describeRequirement(rule, field) {
  const unit = field.unit ? ` ${field.unit}` : ''
  const fieldRequirement = field.requirement || field.required_value
  if (!rule) return fieldRequirement || (field.required ? `Mandatory recorded value${unit}` : 'Record if applicable')
  if (rule.type === 'range') return `${rule.min ?? '-'}${unit} to ${rule.max ?? '-'}${unit}`
  if (rule.type === 'min') return `>= ${rule.min ?? rule.value ?? '-'}${unit}`
  if (rule.type === 'max') return `<= ${rule.max ?? rule.value ?? '-'}${unit}`
  if (rule.type === 'equals') return `= ${rule.value ?? '-'}${unit}`
  if (rule.type === 'not_equals') return `Not ${rule.value ?? '-'}${unit}`
  if (rule.type === 'contains') return `Observation contains "${rule.value ?? '-'}"`
  if (rule.type === 'required') return fieldRequirement || 'Mandatory recorded value'
  return 'Defined by catalog rule'
}

function describeRule(rule) {
  if (!rule) return 'Catalog input schema'
  return `${rule.type || 'Rule'} evaluation`
}

function DynamicField({ field, value, onChange }) {
  const commonProps = {
    id: field.name,
    className: 'input-field',
    value,
    required: Boolean(field.required),
    onChange: (event) => onChange(field.name, event.target.value, field.type),
  }

  return (
    <div>
      <label className="label-field" htmlFor={field.name}>
        {field.label}
        {field.required ? <span className="text-amber"> *</span> : null}
      </label>
      <div className="flex items-center gap-2">
        {field.type === 'textarea' ? (
          <textarea {...commonProps} rows={3} />
        ) : field.type === 'select' ? (
          <select {...commonProps}>
            <option value="">Select...</option>
            {(field.options || []).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        ) : (
          <input {...commonProps} type={field.type || 'text'} />
        )}
        {field.unit ? <span className="text-sm text-slate-400">{field.unit}</span> : null}
      </div>
    </div>
  )
}

function EvaluationPanel({ evaluation, result }) {
  const status = evaluation?.status || result || 'NOT EVALUATED'
  const failedRules = evaluation?.failed_rules || []
  const details = evaluation?.evaluation_details || []

  return (
    <section className="rounded-lg border border-slate-700 bg-navy/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-amber">Evaluation</h2>
          <p className="mt-1 text-sm text-slate-400">
            Automatic pass/fail evaluation based on the ISO catalog rules.
          </p>
        </div>
        <EvaluationBadge status={status} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-slate-700 p-3">
          <p className="text-xs uppercase text-slate-500">Score</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">
            {evaluation?.score === null || evaluation?.score === undefined
              ? 'N/A'
              : `${evaluation.score}%`}
          </p>
        </div>
        <div className="rounded-md border border-slate-700 p-3">
          <p className="text-xs uppercase text-slate-500">Failed Rules</p>
          <p className="mt-1 text-xl font-semibold text-slate-100">{failedRules.length}</p>
        </div>
      </div>

      {failedRules.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-slate-200">Failed Rules</p>
          <ul className="space-y-1 text-sm text-red-300">
            {failedRules.map((rule, index) => (
              <li key={`${rule.field}-${index}`}>{rule.message}</li>
            ))}
          </ul>
        </div>
      )}

      {details.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-slate-200">Evaluation Details</p>
          <div className="space-y-2 text-sm">
            {details.map((detail, index) => (
              <div
                key={`${detail.field}-${index}`}
                className="flex flex-col gap-1 rounded-md border border-slate-700 p-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <span className="text-slate-300">
                  {formatEvaluationLabel(detail.field)} - {formatEvaluationLabel(detail.type)}
                </span>
                <span className={detail.passed ? 'text-emerald-300' : 'text-red-300'}>
                  {detail.passed ? 'Passed' : 'Failed'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function EvaluationBadge({ status }) {
  const styles = {
    PASS: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
    FAIL: 'bg-red-500/20 text-red-300 border border-red-500/40',
    'CONDITIONAL PASS': 'bg-amber/20 text-amber border border-amber/40',
    'NOT EVALUATED': 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
  }
  return (
    <span className={`badge ${styles[status] || styles['NOT EVALUATED']}`}>
      {status}
    </span>
  )
}

function NumberField({ label, value, onChange }) {
  return (
    <div>
      <label className="label-field text-xs">{label}</label>
      <input
        type="number"
        className="input-field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}

function TextAreaField({ label, value, onChange }) {
  return (
    <div>
      <label className="label-field">{label}</label>
      <textarea
        rows={2}
        className="input-field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  )
}
