import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import toast from 'react-hot-toast'
import DUTRegistration from './DUTRegistration'
import { createDut, listDuts } from '../api'

vi.mock('../api', () => ({
  createDut: vi.fn(),
  deleteDut: vi.fn(),
  listDuts: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/dut']}>
      <Routes>
        <Route path="/dut" element={<DUTRegistration />} />
        <Route path="/plan/:dutId" element={<div>Plan view</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DUTRegistration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listDuts.mockResolvedValue([])
  })

  it('blocks submission when minimum temperature exceeds maximum temperature', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByText(/No DUT records are available/i)
    await user.type(screen.getByLabelText('DUT Name *'), 'Body Control Module')

    const minInput = screen.getByLabelText(/Min\. Operating Temperature/i)
    const maxInput = screen.getByLabelText(/Max\. Operating Temperature/i)
    await user.clear(minInput)
    await user.type(minInput, '100')
    await user.clear(maxInput)
    await user.type(maxInput, '50')

    await user.click(screen.getByRole('button', { name: /Save and Generate Test Plan/i }))

    expect(toast.error).toHaveBeenCalledWith(
      'Minimum operating temperature cannot be greater than maximum temperature.',
    )
    expect(createDut).not.toHaveBeenCalled()
  })

  it('rejects a whitespace-only DUT name', async () => {
    // The name field also has a native HTML `required` attribute, which only
    // blocks a truly empty value - a whitespace-only value passes native
    // validation, so this exercises the component's own `.trim()` check.
    const user = userEvent.setup()
    renderPage()

    await screen.findByText(/No DUT records are available/i)
    await user.type(screen.getByLabelText('DUT Name *'), '   ')
    await user.click(screen.getByRole('button', { name: /Save and Generate Test Plan/i }))

    expect(toast.error).toHaveBeenCalledWith('DUT name is required.')
    expect(createDut).not.toHaveBeenCalled()
  })

  it('submits the form and navigates to the generated plan on success', async () => {
    const user = userEvent.setup()
    createDut.mockResolvedValue({ id: 42 })
    renderPage()

    await screen.findByText(/No DUT records are available/i)
    await user.type(screen.getByLabelText('DUT Name *'), 'Body Control Module')
    await user.click(screen.getByRole('button', { name: /Save and Generate Test Plan/i }))

    await waitFor(() => expect(createDut).toHaveBeenCalledTimes(1))
    expect(toast.success).toHaveBeenCalledWith('DUT saved successfully.')
    await screen.findByText('Plan view')
  })
})
