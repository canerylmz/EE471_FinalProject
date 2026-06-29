import { Navigate, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Navbar from './components/Navbar'
import DUTRegistration from './pages/DUTRegistration'
import TestPlan from './pages/TestPlan'
import Checklist from './pages/Checklist'
import ResultReport from './pages/ResultReport'
import Dashboard from './pages/Dashboard'
import TestCatalog from './pages/TestCatalog'
import Equipment from './pages/Equipment'

export default function App() {
  return (
    <div className="min-h-screen bg-navy">
      <Navbar />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
          },
          success: { iconTheme: { primary: '#f59e0b', secondary: '#0f172a' } },
        }}
      />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<Navigate to="/dut" replace />} />
          <Route path="/dut" element={<DUTRegistration />} />
          <Route path="/plan/:dutId" element={<TestPlan />} />
          <Route path="/checklist/:dutId/:testId" element={<Checklist />} />
          <Route path="/result/:dutId/:testId" element={<ResultReport />} />
          <Route path="/catalog" element={<TestCatalog />} />
          <Route path="/equipment" element={<Equipment />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<Navigate to="/dut" replace />} />
        </Routes>
      </main>
    </div>
  )
}
