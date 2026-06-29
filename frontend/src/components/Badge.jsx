const CATEGORY_STYLES = {
  Electrical: 'bg-amber/20 text-amber border border-amber/40',
  electrical: 'bg-amber/20 text-amber border border-amber/40',
  Climatic: 'bg-sky-500/20 text-sky-300 border border-sky-500/40',
  environmental: 'bg-sky-500/20 text-sky-300 border border-sky-500/40',
  Chemical: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
  chemical: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
  general: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
}

const STATUS_STYLES = {
  Mandatory: 'bg-red-500/20 text-red-300 border border-red-500/40',
  Optional: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
  'Not Applicable': 'bg-slate-700/40 text-slate-500 border border-slate-600/40',
}

const RESULT_STYLES = {
  Pass: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
  Fail: 'bg-red-500/20 text-red-300 border border-red-500/40',
  'Conditional Pass': 'bg-amber/20 text-amber border border-amber/40',
  Pending: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
}

const SEVERITY_STYLES = {
  I: 'bg-red-500/20 text-red-300 border border-red-500/40',
  II: 'bg-amber/20 text-amber border border-amber/40',
  III: 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
}

export function CategoryBadge({ category }) {
  return (
    <span className={`badge ${CATEGORY_STYLES[category] || CATEGORY_STYLES.Electrical}`}>
      {category}
    </span>
  )
}

export function StatusBadge({ status }) {
  return (
    <span className={`badge ${STATUS_STYLES[status] || STATUS_STYLES.Optional}`}>{status}</span>
  )
}

export function ResultBadge({ result }) {
  return (
    <span className={`badge ${RESULT_STYLES[result] || RESULT_STYLES.Pending}`}>
      {result || 'Pending'}
    </span>
  )
}

export function SeverityBadge({ severity }) {
  return (
    <span className={`badge ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.III}`}>
      Level {severity}
    </span>
  )
}
