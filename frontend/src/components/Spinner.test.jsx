import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Spinner from './Spinner'

describe('Spinner', () => {
  it('renders a status indicator without a label by default', () => {
    render(<Spinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText(/.+/, { selector: 'p' })).not.toBeInTheDocument()
  })

  it('renders the label text when provided', () => {
    render(<Spinner label="Generating ISO 16750 test plan..." />)
    expect(screen.getByText('Generating ISO 16750 test plan...')).toBeInTheDocument()
  })

  it('falls back to the medium size for an unrecognized size prop', () => {
    render(<Spinner size="huge" />)
    const indicator = screen.getByRole('status')
    expect(indicator.className).toContain('h-8')
  })
})
