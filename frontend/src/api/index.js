import client, { unwrap } from './client'

// --- DUT ---
export const createDut = (data) => unwrap(client.post('/dut', data))
export const listDuts = () => unwrap(client.get('/dut'))
export const getDut = (dutId) => unwrap(client.get(`/dut/${dutId}`))
export const deleteDut = (dutId) => unwrap(client.delete(`/dut/${dutId}`))

// --- Plan ---
export const generatePlan = (dutId) => unwrap(client.post('/plan/generate', { dut_id: dutId }))
export const getPlan = (dutId) => unwrap(client.get(`/plan/${dutId}`))
export const getTest = (testId) => unwrap(client.get(`/plan/test/${testId}`))
export const exportPlan = (dutId) =>
  client.post('/plan/export', { dut_id: dutId }, { responseType: 'blob' })
export const getPlanItems = (dutId) => unwrap(client.get(`/plan/items/${dutId}`))
export const getPlanItem = (planItemId) => unwrap(client.get(`/plan/item/${planItemId}`))
export const updatePlanItemStatus = (planItemId, status) =>
  unwrap(client.patch(`/plan/item/${planItemId}/status`, { status }))
export const updatePlanItemOrder = (planItemId, sortOrder) =>
  unwrap(client.patch(`/plan/item/${planItemId}/order`, { sort_order: sortOrder }))

// --- Checklist ---
export const generateChecklist = (dutId, testId) =>
  unwrap(client.post('/checklist/generate', { dut_id: dutId, test_id: testId }))
export const exportChecklist = (checklistData) =>
  client.post('/checklist/export', { checklist_data: checklistData }, { responseType: 'blob' })

// --- Result & Report ---
export const saveResult = (data) => unwrap(client.post('/result', data))
export const getResult = (testId) => unwrap(client.get(`/result/${testId}`))
export const getResultSchema = (testId) => unwrap(client.get(`/result/schema/${testId}`))
export const evaluateResult = (testId, measuredValues) =>
  unwrap(client.post(`/result/evaluate/${testId}`, { measured_values: measuredValues }))
export const generateReport = (dutId, testId, resultData) =>
  unwrap(
    client.post('/report/generate', {
      dut_id: dutId,
      test_id: testId,
      result_data: resultData,
    }),
  )
export const exportReportDocx = (dutId, testId) =>
  client.post('/report/export/docx', { dut_id: dutId, test_id: testId }, { responseType: 'blob' })
export const exportReportPdf = (dutId, testId) =>
  client.post('/report/export/pdf', { dut_id: dutId, test_id: testId }, { responseType: 'blob' })
export const generateTestRecordForm = (testId) =>
  client.post(`/record-form/generate/${testId}`, {}, { responseType: 'blob' })
export const generateTechnicalReport = (dutId, category = 'all', useAi = false) =>
  client.post(
    `/technical-report/generate/${dutId}`,
    { category, format: 'docx', use_ai: useAi },
    { responseType: 'blob' },
  )

// --- Attachments ---
export const uploadAttachment = (formData) =>
  unwrap(client.post('/attachments/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }))
export const listTestAttachments = (testId) =>
  unwrap(client.get(`/attachments/test/${testId}`))
export const listDutAttachments = (dutId) =>
  unwrap(client.get(`/attachments/dut/${dutId}`))
export const downloadAttachment = (attachmentId) =>
  client.get(`/attachments/download/${attachmentId}`, { responseType: 'blob' })
export const deleteAttachment = (attachmentId) =>
  unwrap(client.delete(`/attachments/${attachmentId}`))

// --- Equipment ---
export const listEquipment = () => unwrap(client.get('/equipment'))
export const createEquipment = (data) => unwrap(client.post('/equipment', data))
export const getEquipment = (equipmentId) => unwrap(client.get(`/equipment/${equipmentId}`))
export const updateEquipment = (equipmentId, data) =>
  unwrap(client.patch(`/equipment/${equipmentId}`, data))
export const deleteEquipment = (equipmentId) => unwrap(client.delete(`/equipment/${equipmentId}`))
export const linkEquipmentToTest = (testId, equipmentId, usageRole = '') =>
  unwrap(client.post('/equipment/link', { test_id: testId, equipment_id: equipmentId, usage_role: usageRole }))
export const listTestEquipment = (testId) => unwrap(client.get(`/equipment/test/${testId}`))
export const unlinkEquipment = (linkId) => unwrap(client.delete(`/equipment/link/${linkId}`))

// --- Dashboard ---
export const getDashboardSummary = () => unwrap(client.get('/dashboard/summary'))
export const getDashboardOverview = () => unwrap(client.get('/dashboard/overview'))
export const getDemoStatus = () => unwrap(client.get('/demo/status'))
export const seedDemoData = (resetDemoData = false) =>
  unwrap(client.post('/demo/seed', { reset_demo_data: resetDemoData }))

// --- ISO Test Catalog ---
export const listCatalogTests = (filters = {}) =>
  unwrap(client.get('/catalog/tests', { params: filters }))
export const getCatalogTest = (catalogId) => unwrap(client.get(`/catalog/tests/${catalogId}`))
