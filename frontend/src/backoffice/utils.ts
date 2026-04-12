export function matches(search: string, values: Array<string | number | boolean | null | undefined>) {
  if (!search) return true
  return values.some((value) => String(value ?? '').toLowerCase().includes(search))
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export function effectiveCodeFromPropertyCode(value: string) {
  const digits = value.replace(/\D/g, '')
  if (!digits) return ''
  return digits.slice(-3).padStart(3, '0')
}
