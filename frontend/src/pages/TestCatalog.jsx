import { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { listCatalogTests } from '../api'
import Spinner from '../components/Spinner'

const ALL = ''

export default function TestCatalog() {
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ category: ALL, iso_part: ALL })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listCatalogTests({
        category: filters.category || undefined,
        iso_part: filters.iso_part || undefined,
      })
      setTests(data.tests || [])
    } catch (err) {
      toast.error(err.message || 'Test catalog could not be loaded.')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    load()
  }, [load])

  const options = useMemo(() => {
    const unique = (values) => [...new Set(values.filter(Boolean))].sort()
    return {
      categories: unique(tests.map((test) => test.category)),
      isoParts: unique(tests.map((test) => test.iso_part)),
    }
  }, [tests])

  const handleFilterChange = (key) => (event) => {
    setFilters((prev) => ({ ...prev, [key]: event.target.value }))
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Test Catalog</h1>
          <p className="mt-1 text-sm text-slate-400">
            Browse structured ISO 16750 test metadata used by the planning engine.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FilterSelect
            label="Category"
            value={filters.category}
            onChange={handleFilterChange('category')}
            options={options.categories}
          />
          <FilterSelect
            label="ISO Part"
            value={filters.iso_part}
            onChange={handleFilterChange('iso_part')}
            options={options.isoParts}
          />
        </div>
      </div>

      <div className="card overflow-x-auto">
        {loading ? (
          <Spinner label="Catalog loading..." />
        ) : (
          <table className="min-w-full divide-y divide-slate-700 text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                <th className="px-3 py-2">ISO Part</th>
                <th className="px-3 py-2">Clause</th>
                <th className="px-3 py-2">Test Name</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Operating Mode</th>
                <th className="px-3 py-2">Functional Status</th>
                <th className="px-3 py-2">Required Test Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {tests.map((test) => (
                <tr key={test.id} className="hover:bg-navy/60">
                  <td className="whitespace-nowrap px-3 py-3 font-medium text-amber">
                    {test.iso_part}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-300">
                    {test.clause_number || '-'}
                  </td>
                  <td className="min-w-64 px-3 py-3 text-slate-100">{test.test_name}</td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-300">
                    {test.category}
                  </td>
                  <td className="min-w-48 px-3 py-3 text-slate-300">
                    {test.operating_mode || '-'}
                  </td>
                  <td className="min-w-48 px-3 py-3 text-slate-300">
                    {test.functional_status || '-'}
                  </td>
                  <td className="min-w-56 px-3 py-3 text-slate-300">
                    {test.required_test_level || '-'}
                  </td>
                </tr>
              ))}
              {tests.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-slate-400">
                    No catalog tests match the selected filters. Clear the filters or seed the ISO catalog.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div>
      <label className="label-field">{label}</label>
      <select className="input-field" value={value} onChange={onChange}>
        <option value={ALL}>All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  )
}
