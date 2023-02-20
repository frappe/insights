export const COLOR_MAP = {
	pink: '#F683AE',
	blue: '#318AD8',
	green: '#48BB74',
	red: '#F56B6B',
	yellow: '#FACF7A',
	purple: '#44427B',
	teal: '#5FD8C4',
	cyan: '#15CCEF',
	orange: '#F8814F',
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

const LIGHT_COLOR_MAP = {
	'light-pink': '#FED7E5',
	'light-blue': '#BFDDF7',
	'light-green': '#48BB74',
	'light-grey': '#F4F5F6',
	'light-red': '#F6DFDF',
	'light-yellow': '#FEE9BF',
	'light-purple': '#E8E8F7',
	'light-teal': '#D3FDF6',
	'light-cyan': '#DDF8FD',
	'light-orange': '#FECDB8',
}

export const randomColor = (num = 1) => {
	const colors = []
	let hue = Math.floor(Math.random() * 360)
	let lightness = '65%'
	let alpha = 1
	for (let i = 0; i < num; i++) {
		const color = `hsla(${hue}, 50%, ${lightness}, ${alpha})`
		colors.push(color)
		hue = Math.floor(Math.random() * 360)
	}
	return colors
}

export const getColors = (num = Object.keys(COLOR_MAP).length) => {
	if (num == 1) {
		return randomColor()
	}
	const colors = []
	const _colors = Object.values(COLOR_MAP)
	for (let i = 0; i < num; i++) {
		colors.push(_colors[i % _colors.length])
	}
	return colors
}
