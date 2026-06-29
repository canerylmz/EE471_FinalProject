/**
 * Trigger a browser download for a Blob, parsing the filename from a
 * Content-Disposition header when available.
 */
export function downloadBlob(blob, fallbackFilename, contentDisposition) {
  let filename = fallbackFilename
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) {
      filename = match[1]
    }
  }

  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export function downloadFromResponse(response, fallbackFilename) {
  downloadBlob(response.data, fallbackFilename, response.headers?.['content-disposition'])
}
