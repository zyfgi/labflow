import client from './client'

export interface Equipment {
  id: number
  asset_no: string
  name: string
  category: string
  manufacturer: string | null
  model: string | null
  serial_no: string | null
  location: string | null
  manager_id: number | null
  manager_name?: string | null
  status: string
  description: string | null
  manual_url: string | null
  booking_required: boolean
  is_active: boolean
  next_booking?: { id: number; start_time: string; end_time: string; user_name: string | null } | null
  latest_maintenance?: { id: number; type: string; status: string; reported_at: string | null } | null
}

export interface EquipmentBooking {
  id: number
  equipment_id: number
  equipment_name?: string
  user_id: number
  user_name?: string | null
  project_id: number | null
  start_time: string
  end_time: string
  purpose: string | null
  status: string
  approved_by: number | null
  approved_at: string | null
}

export interface EquipmentBorrow {
  id: number
  equipment_id: number
  equipment_name?: string
  borrower_id: number
  borrower_name?: string | null
  borrow_time: string | null
  expected_return_time: string | null
  actual_return_time: string | null
  purpose: string | null
  status: string
  note: string | null
  is_overdue?: boolean
}

export interface EquipmentMaintenance {
  id: number
  equipment_id: number
  equipment_name?: string
  reporter_id: number | null
  reporter_name?: string | null
  type: string
  description: string | null
  reported_at: string | null
  started_at: string | null
  finished_at: string | null
  status: string
  cost: string | null
  vendor: string | null
  result: string | null
}

export function listEquipment(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: Equipment[]; total: number } }>('/equipment', { params })
}

export function getEquipment(id: number) {
  return client.get<{ data: Equipment }>(`/equipment/${id}`)
}

export function createEquipment(payload: Record<string, unknown>) {
  return client.post('/equipment', payload)
}

export function updateEquipment(id: number, payload: Record<string, unknown>) {
  return client.patch(`/equipment/${id}`, payload)
}

export function listBookings(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: EquipmentBooking[]; total: number } }>('/equipment-bookings', { params })
}

export function createBooking(payload: Record<string, unknown>) {
  return client.post('/equipment-bookings', payload)
}

export function bookingAction(id: number, action: 'approve' | 'reject' | 'cancel') {
  return client.post(`/equipment-bookings/${id}/${action}`)
}

export function listBorrows(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: EquipmentBorrow[]; total: number } }>('/equipment-borrows', { params })
}

export function createBorrow(payload: Record<string, unknown>) {
  return client.post('/equipment-borrows', payload)
}

export function returnBorrow(id: number) {
  return client.post(`/equipment-borrows/${id}/return`)
}

export function listMaintenance(params: Record<string, unknown> = {}) {
  return client.get<{ data: { items: EquipmentMaintenance[]; total: number } }>('/equipment-maintenance', { params })
}

export function createMaintenance(payload: Record<string, unknown>) {
  return client.post('/equipment-maintenance', payload)
}

export function updateMaintenance(id: number, payload: Record<string, unknown>) {
  return client.patch(`/equipment-maintenance/${id}`, payload)
}
