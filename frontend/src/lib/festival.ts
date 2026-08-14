export type FestivalId =
  | 'normal'
  | 'newyear'
  | 'republic'
  | 'holi'
  | 'pongal'
  | 'independence'
  | 'diwali'
  | 'christmas'

export interface FestivalInfo {
  id: FestivalId
  label: string
}

interface FestivalWindow {
  id: FestivalId
  label: string
  start: string
  end: string
}

const WINDOWS: FestivalWindow[] = [
  { id: 'newyear', label: 'New Year', start: '01-01', end: '01-02' },
  { id: 'pongal', label: 'Pongal', start: '01-13', end: '01-17' },
  { id: 'republic', label: 'Republic Day', start: '01-25', end: '01-27' },
  { id: 'holi', label: 'Holi', start: '03-03', end: '03-05' },
  { id: 'independence', label: 'Independence Day', start: '08-14', end: '08-16' },
  { id: 'diwali', label: 'Diwali', start: '11-06', end: '11-10' },
  { id: 'christmas', label: 'Christmas', start: '12-24', end: '12-26' },
]

const NORMAL: FestivalInfo = { id: 'normal', label: 'Normal' }

export function getActiveFestival(date: Date = new Date()): FestivalInfo {
  const mmdd = `${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`
  for (const window of WINDOWS) {
    if (mmdd >= window.start && mmdd <= window.end) {
      return { id: window.id, label: window.label }
    }
  }
  return NORMAL
}