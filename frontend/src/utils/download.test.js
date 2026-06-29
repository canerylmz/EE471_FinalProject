import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadBlob, downloadFromResponse } from './download'

describe('downloadBlob', () => {
  let createElementSpy

  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
    // jsdom doesn't implement real navigation; stub click() so it doesn't
    // log "Not implemented: navigation" noise for the blob: anchor.
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    createElementSpy = vi.spyOn(document, 'createElement')
  })

  afterEach(() => {
    createElementSpy.mockRestore()
  })

  it('uses the fallback filename when no content-disposition header is given', () => {
    downloadBlob(new Blob(['data']), 'report.docx', null)

    const anchor = createElementSpy.mock.results[0].value
    expect(anchor.download).toBe('report.docx')
    expect(window.URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
  })

  it('extracts the filename from a quoted content-disposition header', () => {
    downloadBlob(new Blob(['data']), 'fallback.docx', 'attachment; filename="CH-001-ISO16750.docx"')

    const anchor = createElementSpy.mock.results[0].value
    expect(anchor.download).toBe('CH-001-ISO16750.docx')
  })

  it('falls back to the default filename when the header has no filename', () => {
    downloadBlob(new Blob(['data']), 'fallback.docx', 'attachment')

    const anchor = createElementSpy.mock.results[0].value
    expect(anchor.download).toBe('fallback.docx')
  })
})

describe('downloadFromResponse', () => {
  let createElementSpy

  beforeEach(() => {
    window.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
    window.URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    createElementSpy = vi.spyOn(document, 'createElement')
  })

  afterEach(() => {
    createElementSpy.mockRestore()
  })

  it('reads the blob and content-disposition header from an axios-style response', () => {
    const response = {
      data: new Blob(['data']),
      headers: { 'content-disposition': 'attachment; filename="Result.pdf"' },
    }

    downloadFromResponse(response, 'fallback.pdf')

    const anchor = createElementSpy.mock.results[0].value
    expect(anchor.download).toBe('Result.pdf')
  })

  it('falls back to the default filename when the response has no headers', () => {
    const response = { data: new Blob(['data']) }

    downloadFromResponse(response, 'fallback.pdf')

    const anchor = createElementSpy.mock.results[0].value
    expect(anchor.download).toBe('fallback.pdf')
  })
})
