import { NavLink } from 'react-router-dom'

const links = [
  { to: '/catalog', label: 'Test Catalog' },
  { to: '/equipment', label: 'Equipment' },
  { to: '/dut', label: 'DUT Registration' },
  { to: '/dashboard', label: 'Campaign Dashboard' },
]

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-navy/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <NavLink to="/dut" className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber font-bold text-navy">
            TF
          </span>
          <span className="text-lg font-bold tracking-tight text-slate-100">
            Test<span className="text-amber">Forge</span>
          </span>
        </NavLink>

        <nav className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? 'bg-amber/10 text-amber'
                    : 'text-slate-300 hover:bg-navy-light hover:text-amber'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
