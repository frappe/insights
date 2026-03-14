export const COLOR_MAP = {
	blue: '#318AD8',
	pink: '#F683AE',
	green: '#48BB74',
	red: '#F56B6B',
	yellow: '#FACF7A',
	purple: '#44427B',
	teal: '#5FD8C4',
	orange: '#F8814F',
	cyan: '#15CCEF',
	grey: '#A6B1B9',
	'#449CF0': '#449CF0',
	'#ECAD4B': '#ECAD4B',
	'#761ACB': '#761ACB',
	'#CB2929': '#CB2929',
	'#ED6396': '#ED6396',
	'#29CD42': '#29CD42',
	'#4463F0': '#4463F0',
	'#EC864B': '#EC864B',
	'#4F9DD9': '#4F9DD9',
	'#39E4A5': '#39E4A5',
	'#B4CD29': '#B4CD29',
}

// https://10015.io/tools/color-shades-generator
export const GRADIENT_COLORS = {
	blue: [
		'#2d87d6',
		'#4393da',
		'#589fdf',
		'#6dace3',
		'#83b8e7',
		'#98c4eb',
		'#c3dcf3',
		'#d8e9f7',
		'#edf5fc',
		'#ffffff',
	],
}

export const getColors = () => {
	return Object.values(COLOR_MAP)
}

export const getGradientColors = (color: keyof typeof GRADIENT_COLORS) => {
	return GRADIENT_COLORS[color]
}

export type HashString = `#${string}`
export type RGBString = `rgb(${number}, ${number}, ${number})`

export function getRGB(color: HashString | RGBString | string | null): HashString {
	if (!color) {
		return '#ffffff'
	}
	if (color.startsWith('rgb')) {
		return RGBToHex(color as RGBString)
	} else if (!color.startsWith('#') && color.match(/\b[a-fA-F0-9]{3,6}\b/g)) {
		return `#${color}` as HashString
	}
	return color as HashString
}

export function RGBToHex(rgb: RGBString): HashString {
	const [r, g, b] = rgb
		.replace('rgb(', '')
		.replace(')', '')
		.split(',')
		.map((x) => parseInt(x))
	return `#${[r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('')}`
}

export function HSVToHex(h: number, s: number, v: number): HashString {
	s /= 100
	v /= 100
	h /= 360

	let r = 0,
		g = 0,
		b = 0

	let i = Math.floor(h * 6)
	let f = h * 6 - i
	let p = v * (1 - s)
	let q = v * (1 - f * s)
	let t = v * (1 - (1 - f) * s)

	switch (i % 6) {
		case 0:
			;(r = v), (g = t), (b = p)
			break
		case 1:
			;(r = q), (g = v), (b = p)
			break
		case 2:
			;(r = p), (g = v), (b = t)
			break
		case 3:
			;(r = p), (g = q), (b = v)
			break
		case 4:
			;(r = t), (g = p), (b = v)
			break
		case 5:
			;(r = v), (g = p), (b = q)
			break
	}
	r = Math.round(r * 255)
	g = Math.round(g * 255)
	b = Math.round(b * 255)
	return `#${[r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('')}`
}

export function HexToHSV(color: HashString): { h: number; s: number; v: number } {
	const [r, g, b] = color
		.replace('#', '')
		.match(/.{1,2}/g)
		?.map((x) => parseInt(x, 16)) || [0, 0, 0]

	const max = Math.max(r, g, b)
	const min = Math.min(r, g, b)
	const v = max / 255
	const d = max - min
	const s = max === 0 ? 0 : d / max
	const h =
		max === min
			? 0
			: max === r
			? (g - b) / d + (g < b ? 6 : 0)
			: max === g
			? (b - r) / d + 2
			: (r - g) / d + 4
	return { h: h * 60, s, v }
}
