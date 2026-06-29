export default function Spinner({ size = 'md', label }) {
  const sizes = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-2',
    lg: 'h-12 w-12 border-4',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-6 text-slate-300">
      <div
        className={`${sizes[size] || sizes.md} animate-spin rounded-full border-amber border-t-transparent`}
        role="status"
        aria-label="loading"
      />
      {label && <p className="text-sm">{label}</p>}
    </div>
  )
}
