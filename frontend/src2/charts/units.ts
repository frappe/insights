import { AxisUnit } from '../types/chart.types'

type Scale = { unit: AxisUnit; factor: number; suffix: string }

const TIME_SCALES_IN_SECONDS: Scale[] = [
	{ unit: 'ns', factor: 1e-9, suffix: 'ns' },
	{ unit: 'us', factor: 1e-6, suffix: 'µs' },
	{ unit: 'ms', factor: 1e-3, suffix: 'ms' },
	{ unit: 's', factor: 1, suffix: 's' },
	{ unit: 'min', factor: 60, suffix: 'min' },
	{ unit: 'h', factor: 3600, suffix: 'h' },
	{ unit: 'd', factor: 86400, suffix: 'd' },
	{ unit: 'w', factor: 604800, suffix: 'w' },
	{ unit: 'mo', factor: 2629800, suffix: 'mo' },
	{ unit: 'y', factor: 31557600, suffix: 'y' },
]

const DATA_SCALES_IN_BYTES: Scale[] = [
	{ unit: 'bytes', factor: 1, suffix: 'B' },
	{ unit: 'KB', factor: 1024, suffix: 'KB' },
	{ unit: 'MB', factor: 1024 ** 2, suffix: 'MB' },
	{ unit: 'GB', factor: 1024 ** 3, suffix: 'GB' },
	{ unit: 'TB', factor: 1024 ** 4, suffix: 'TB' },
]

const TIME_UNITS = new Set(TIME_SCALES_IN_SECONDS.map((s) => s.unit))
const DATA_UNITS = new Set(DATA_SCALES_IN_BYTES.map((s) => s.unit))

export type UnitGroupOption = { group: string; label: string; value: AxisUnit }

export const UNIT_OPTIONS: UnitGroupOption[] = [
	{ group: 'None', label: 'None', value: 'none' },
	{ group: 'Time', label: 'Nanoseconds (ns)', value: 'ns' },
	{ group: 'Time', label: 'Microseconds (µs)', value: 'us' },
	{ group: 'Time', label: 'Milliseconds (ms)', value: 'ms' },
	{ group: 'Time', label: 'Seconds (s)', value: 's' },
	{ group: 'Time', label: 'Minutes (min)', value: 'min' },
	{ group: 'Time', label: 'Hours (h)', value: 'h' },
	{ group: 'Time', label: 'Days (d)', value: 'd' },
	{ group: 'Time', label: 'Weeks (w)', value: 'w' },
	{ group: 'Time', label: 'Months (mo)', value: 'mo' },
	{ group: 'Time', label: 'Years (y)', value: 'y' },
	{ group: 'Data', label: 'Bytes', value: 'bytes' },
	{ group: 'Data', label: 'Kilobytes (KB)', value: 'KB' },
	{ group: 'Data', label: 'Megabytes (MB)', value: 'MB' },
	{ group: 'Data', label: 'Gigabytes (GB)', value: 'GB' },
	{ group: 'Data', label: 'Terabytes (TB)', value: 'TB' },
]

function getScales(unit: AxisUnit): Scale[] | null {
	if (TIME_UNITS.has(unit)) return TIME_SCALES_IN_SECONDS
	if (DATA_UNITS.has(unit)) return DATA_SCALES_IN_BYTES
	return null
}

function pickScale(baseValue: number, scales: Scale[]): Scale {
	const abs = Math.abs(baseValue)
	if (abs === 0 || !isFinite(abs)) return scales[0]
	let chosen = scales[0]
	for (const s of scales) {
		if (abs >= s.factor) chosen = s
		else break
	}
	return chosen
}

export function hasUnit(unit?: AxisUnit | null): boolean {
	return !!unit && unit !== 'none' && getScales(unit) !== null
}

export function formatValueWithUnit(
	value: number,
	sourceUnit: AxisUnit | undefined,
	precision = 1,
): string {
	if (value === null || value === undefined || isNaN(value as any)) return String(value)
	if (!hasUnit(sourceUnit)) return formatPlain(value, precision)

	const scales = getScales(sourceUnit as AxisUnit)!
	const source = scales.find((s) => s.unit === sourceUnit)!
	const baseValue = value * source.factor
	const target = pickScale(baseValue, scales)
	const scaled = baseValue / target.factor

	return `${stripTrailingZeros(scaled.toFixed(precision))} ${target.suffix}`
}

function formatPlain(value: number, precision: number): string {
	if (Math.abs(value) >= 1000) {
		return new Intl.NumberFormat('en-US', {
			notation: 'compact',
			maximumFractionDigits: precision,
		}).format(value)
	}
	return stripTrailingZeros(value.toFixed(precision))
}

function stripTrailingZeros(s: string): string {
	if (!s.includes('.')) return s
	return s.replace(/\.?0+$/, '')
}
