import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CategoryBadge, ResultBadge, SeverityBadge, StatusBadge } from './Badge'

describe('CategoryBadge', () => {
  it('renders the category label', () => {
    render(<CategoryBadge category="chemical" />)
    expect(screen.getByText('chemical')).toBeInTheDocument()
  })

  it('falls back to the Electrical style for an unknown category', () => {
    render(<CategoryBadge category="unknown-category" />)
    const badge = screen.getByText('unknown-category')
    expect(badge.className).toContain('amber')
  })
})

describe('StatusBadge', () => {
  it('renders Mandatory with the red/danger style', () => {
    render(<StatusBadge status="Mandatory" />)
    const badge = screen.getByText('Mandatory')
    expect(badge.className).toContain('red')
  })
})

describe('ResultBadge', () => {
  it('shows "Pending" when no result is provided', () => {
    render(<ResultBadge result={null} />)
    expect(screen.getByText('Pending')).toBeInTheDocument()
  })

  it('shows Fail with the danger style', () => {
    render(<ResultBadge result="Fail" />)
    const badge = screen.getByText('Fail')
    expect(badge.className).toContain('red')
  })
})

describe('SeverityBadge', () => {
  it('renders the severity level text', () => {
    render(<SeverityBadge severity="II" />)
    expect(screen.getByText('Level II')).toBeInTheDocument()
  })

  it('falls back to severity III style for an unrecognized level', () => {
    render(<SeverityBadge severity="V" />)
    const badge = screen.getByText('Level V')
    expect(badge.className).toContain('slate')
  })
})
