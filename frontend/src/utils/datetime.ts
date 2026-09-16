import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)

/** 后端存 naive UTC；展示时转为本地时间 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  return dayjs.utc(value).local().format('YYYY-MM-DD HH:mm')
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD')
}

export function currentWeekStart(d = new Date()): string {
  const day = d.getDay() === 0 ? 7 : d.getDay() // Monday=1..Sunday=7
  const monday = new Date(d)
  monday.setDate(d.getDate() - (day - 1))
  return dayjs(monday).format('YYYY-MM-DD')
}

export function weekEndOf(weekStart: string): string {
  return dayjs(weekStart).add(6, 'day').format('YYYY-MM-DD')
}

export function today(): string {
  return dayjs().format('YYYY-MM-DD')
}
