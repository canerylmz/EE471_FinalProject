import { useNavigate } from 'react-router-dom'
import { CategoryBadge, ResultBadge, SeverityBadge, StatusBadge } from './Badge'

const PLAN_ITEM_STATUSES = ['planned', 'approved', 'in_progress', 'completed', 'cancelled']

export default function TestCard({ dutId, test, result, onPlanItemStatusChange }) {
  const navigate = useNavigate()
  const equipment = Array.isArray(test.required_equipment) ? test.required_equipment : []

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-semibold text-slate-100">{test.test_name}</h3>
        <ResultBadge result={result?.result} />
      </div>

      <p className="text-xs font-medium text-slate-400">{test.standard_reference}</p>

      <div className="flex items-center justify-between gap-3 rounded-md border border-slate-700 bg-navy/40 px-3 py-2">
        <div className="text-xs text-slate-400">
          <span className="font-medium text-slate-300">Plan Item:</span>{' '}
          {test.planned_test_no || test.test_plan_item_id || '-'}
        </div>
        <select
          className="input-field max-w-36 py-1 text-xs"
          value={test.plan_item_status || 'planned'}
          disabled={!test.test_plan_item_id || !onPlanItemStatusChange}
          onChange={(event) => onPlanItemStatusChange?.(test, event.target.value)}
        >
          {PLAN_ITEM_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
        <Meta label="ISO Part" value={test.iso_part} />
        <Meta label="Clause No" value={test.clause_no} />
        <Meta label="Operating Mode" value={test.operating_mode} />
        <Meta label="Functional Status" value={test.functional_status} />
        <Meta label="Required Level" value={test.required_test_level} />
        <Meta label="Sample Size" value={test.sample_size} />
      </div>

      <div className="flex flex-wrap gap-2">
        <CategoryBadge category={test.category} />
        <StatusBadge status={test.status} />
        <SeverityBadge severity={test.severity_level} />
      </div>

      <div className="text-sm text-slate-300">
        <span className="font-medium text-slate-200">Duration:</span> {test.duration_hours} hours
      </div>

      <div className="text-sm text-slate-300">
        <p className="mb-1 font-medium text-slate-200">Required Equipment:</p>
        {equipment.length > 0 ? (
          <ul className="list-inside list-disc space-y-0.5 text-slate-400">
            {equipment.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-500">Not specified</p>
        )}
      </div>

      <div className="text-sm text-slate-300">
        <p className="mb-1 font-medium text-slate-200">Acceptance Criteria:</p>
        <p className="text-slate-400">{test.acceptance_criteria}</p>
      </div>

      {test.selection_reason && (
        <div className="text-sm text-slate-300">
          <p className="mb-1 font-medium text-slate-200">AI Reason:</p>
          <p className="text-slate-400">{test.selection_reason}</p>
        </div>
      )}

      <div className="mt-2 flex flex-wrap gap-2 border-t border-slate-700 pt-3">
        <button
          type="button"
          className="btn-secondary flex-1"
          onClick={() => navigate(`/checklist/${dutId}/${test.id}`)}
        >
          Generate Checklist
        </button>
        <button
          type="button"
          className="btn-primary flex-1"
          onClick={() => navigate(`/result/${dutId}/${test.id}`)}
        >
          Enter Result
        </button>
      </div>
    </div>
  )
}

function Meta({ label, value }) {
  return (
    <div>
      <span className="font-medium text-slate-300">{label}:</span> {value || '-'}
    </div>
  )
}
