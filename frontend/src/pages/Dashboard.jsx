import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Doughnut } from 'react-chartjs-2'
import { ArcElement, Chart as ChartJS, Legend, Tooltip } from 'chart.js'
import toast from 'react-hot-toast'
import { getDashboardOverview, seedDemoData } from '../api'
import Spinner from '../components/Spinner'

ChartJS.register(ArcElement, Tooltip, Legend)

const chartOptions = {
  plugins: {
    legend: {
      position: 'bottom',
      labels: { color: '#cbd5e1', boxWidth: 12 },
    },
  },
  maintainAspectRatio: false,
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [seedingDemo, setSeedingDemo] = useState(false)
  const [resetDemoData, setResetDemoData] = useState(false)

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    setLoading(true)
    try {
      const overviewData = await getDashboardOverview()
      setData(overviewData)
    } catch (err) {
      toast.error(err.message || 'Dashboard overview could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadDemoData = async () => {
    if (
      resetDemoData &&
      !window.confirm('Reset previously seeded demo data before loading a fresh demo dataset?')
    ) {
      return
    }
    setSeedingDemo(true)
    try {
      const result = await seedDemoData(resetDemoData)
      toast.success(result.created ? 'Demo data loaded.' : 'Demo data is already available.')
      await load()
    } catch (err) {
      toast.error(err.message || 'Demo data could not be loaded.')
    } finally {
      setSeedingDemo(false)
    }
  }

  if (loading) {
    return <Spinner size="lg" label="Loading dashboard..." />
  }

  const summary = data?.summary || {}
  const attention = data?.attention_required || {}
  const workflow = data?.workflow_progress || {}

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">ISO 16750 Project Dashboard</h1>
          <p className="mt-1 text-sm text-slate-400">
            Monitor the ISO 16750 testing workflow and presentation status.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:items-end">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary"
              onClick={handleLoadDemoData}
              disabled={seedingDemo}
            >
              {seedingDemo ? 'Loading Demo Data...' : 'Load Demo Data'}
            </button>
            <Link to="/dut" className="btn-secondary inline-flex justify-center">
              Register DUT
            </Link>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-600 bg-navy-light"
              checked={resetDemoData}
              onChange={(event) => setResetDemoData(event.target.checked)}
            />
            Reset existing demo data first
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="DUTs" value={summary.total_duts || 0} />
        <MetricCard label="Plan Items" value={summary.total_plan_items || 0} />
        <MetricCard label="Tests" value={summary.total_tests || 0} />
        <MetricCard label="Completed Results" value={summary.completed_results || 0} />
        <MetricCard label="PASS" value={summary.pass || 0} tone="pass" />
        <MetricCard label="FAIL" value={summary.fail || 0} tone="fail" />
        <MetricCard label="Attachments" value={summary.attachments || 0} />
        <MetricCard
          label="Equipment Expired"
          value={data?.equipment_calibration_summary?.expired || 0}
          tone="fail"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <ChartCard
          title="Tests by Category"
          data={makeChartData(
            ['Electrical', 'Environmental', 'Chemical'],
            [
              data?.tests_by_category?.electrical || 0,
              data?.tests_by_category?.environmental || 0,
              data?.tests_by_category?.chemical || 0,
            ],
            ['#f59e0b', '#38bdf8', '#10b981'],
          )}
        />
        <ChartCard
          title="Evaluation Status Distribution"
          data={makeChartData(
            ['PASS', 'FAIL', 'CONDITIONAL PASS', 'NOT EVALUATED'],
            [
              data?.results_by_evaluation_status?.PASS || 0,
              data?.results_by_evaluation_status?.FAIL || 0,
              data?.results_by_evaluation_status?.['CONDITIONAL PASS'] || 0,
              data?.results_by_evaluation_status?.['NOT EVALUATED'] || 0,
            ],
            ['#10b981', '#ef4444', '#f59e0b', '#64748b'],
          )}
        />
        <ChartCard
          title="Equipment Calibration Status"
          data={makeChartData(
            ['Valid', 'Due Soon', 'Expired', 'Not Available'],
            [
              data?.equipment_calibration_summary?.valid || 0,
              data?.equipment_calibration_summary?.due_soon || 0,
              data?.equipment_calibration_summary?.expired || 0,
              data?.equipment_calibration_summary?.not_available || 0,
            ],
            ['#10b981', '#f59e0b', '#ef4444', '#64748b'],
          )}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <WorkflowProgress workflow={workflow} />
        <AttentionRequired attention={attention} />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <RecentDuts items={data?.recent_duts || []} />
        <RecentResults items={data?.recent_test_results || []} />
      </div>
    </div>
  )
}

function MetricCard({ label, value, tone = 'default' }) {
  const tones = {
    default: 'text-amber',
    pass: 'text-emerald-300',
    fail: 'text-red-300',
  }
  return (
    <div className="card">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${tones[tone]}`}>{value}</p>
    </div>
  )
}

function ChartCard({ title, data }) {
  const total = data.datasets[0].data.reduce((sum, value) => sum + value, 0)
  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-amber">{title}</h2>
      {total > 0 ? (
        <div className="h-64">
          <Doughnut data={data} options={chartOptions} />
        </div>
      ) : (
        <p className="text-sm text-slate-400">No data is available yet.</p>
      )}
    </div>
  )
}

function WorkflowProgress({ workflow }) {
  const rows = [
    ['DUT Registered', workflow.dut_registered ?? 0],
    ['Test Plan Generated', workflow.test_plan_generated ?? 0],
    ['Results Entered', workflow.results_entered ?? 0],
    ['Evaluation Completed', workflow.evaluation_completed ?? 0],
    ['Record Forms Available', workflow.record_forms_available || 'Available on demand'],
    ['Technical Reports Available', workflow.technical_reports_available || 'Available on demand'],
  ]
  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-amber">Workflow Progress</h2>
      <div className="space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between border-b border-slate-800 pb-2 last:border-0">
            <span className="text-sm text-slate-300">{label}</span>
            <span className="text-sm font-semibold text-slate-100">{value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AttentionRequired({ attention }) {
  const sections = [
    ['Failed Tests', attention.failed_tests || [], (item) => item.test_name || 'Unnamed test'],
    ['Tests Without Results', attention.tests_without_results || [], (item) => item.test_name || 'Unnamed test'],
    ['Expired Equipment', attention.expired_equipment || [], equipmentText],
    ['Due Soon Equipment', attention.due_soon_equipment || [], equipmentText],
  ]
  const total = sections.reduce((sum, [, items]) => sum + items.length, 0)

  return (
    <div className="card">
      <h2 className="mb-3 text-lg font-semibold text-amber">Attention Required</h2>
      {total === 0 ? (
        <p className="text-sm text-slate-400">No attention items are currently listed.</p>
      ) : (
        <div className="space-y-4">
          {sections.map(([title, items, render]) =>
            items.length > 0 ? (
              <div key={title}>
                <p className="mb-2 text-sm font-semibold text-slate-200">{title}</p>
                <ul className="space-y-1 text-sm text-slate-400">
                  {items.slice(0, 4).map((item, index) => (
                    <li key={`${title}-${index}`} className="rounded-md border border-slate-800 px-2 py-1">
                      {render(item)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
        </div>
      )}
    </div>
  )
}

function RecentDuts({ items }) {
  return (
    <div className="card overflow-x-auto">
      <h2 className="mb-3 text-lg font-semibold text-amber">Recent DUTs</h2>
      <SimpleTable
        columns={['DUT', 'Client', 'Project']}
        rows={items.map((item) => [
          <Link key="dut" to={`/plan/${item.id}`} className="text-amber hover:underline">
            {item.name || '-'}
          </Link>,
          item.customer || '-',
          item.project || '-',
        ])}
        emptyText="No DUT records are available yet."
      />
    </div>
  )
}

function RecentResults({ items }) {
  return (
    <div className="card overflow-x-auto">
      <h2 className="mb-3 text-lg font-semibold text-amber">Recent Test Results</h2>
      <SimpleTable
        columns={['DUT', 'Test', 'Evaluation']}
        rows={items.map((item) => [
          item.dut_name || '-',
          <Link key="test" to={`/result/${item.dut_id}/${item.test_id}`} className="text-amber hover:underline">
            {item.test_name || '-'}
          </Link>,
          <StatusBadge key="status" status={item.evaluation_status} />,
        ])}
        emptyText="No test results have been entered yet."
      />
    </div>
  )
}

function SimpleTable({ columns, rows, emptyText }) {
  return (
    <table className="min-w-full divide-y divide-slate-700 text-sm">
      <thead>
        <tr className="text-left text-xs uppercase text-slate-500">
          {columns.map((column) => (
            <th key={column} className="px-3 py-2">{column}</th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-800">
        {rows.length === 0 ? (
          <tr>
            <td className="px-3 py-3 text-slate-400" colSpan={columns.length}>
              {emptyText}
            </td>
          </tr>
        ) : (
          rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="px-3 py-2 text-slate-300">{cell}</td>
              ))}
            </tr>
          ))
        )}
      </tbody>
    </table>
  )
}

function StatusBadge({ status }) {
  const styles = {
    PASS: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
    FAIL: 'bg-red-500/20 text-red-300 border border-red-500/40',
    'CONDITIONAL PASS': 'bg-amber/20 text-amber border border-amber/40',
    'NOT EVALUATED': 'bg-slate-500/20 text-slate-300 border border-slate-500/40',
  }
  return <span className={`badge ${styles[status] || styles['NOT EVALUATED']}`}>{status || 'NOT EVALUATED'}</span>
}

function makeChartData(labels, values, colors) {
  return {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: colors,
        borderColor: '#0f172a',
        borderWidth: 2,
      },
    ],
  }
}

function equipmentText(item) {
  const label = [item.equipment_no, item.kind_of_equipment].filter(Boolean).join(' - ') || 'Equipment'
  const date = item.next_calibration_date ? `, next calibration: ${item.next_calibration_date}` : ''
  return `${label}${date}`
}
