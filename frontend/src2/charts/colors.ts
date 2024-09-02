
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

export const getColors = (num = Object.keys(COLOR_MAP).length) => {
	const colors = []
	const _colors = Object.values(COLOR_MAP)
	for (let i = 0; i < num; i++) {
		colors.push(_colors[i % _colors.length])
	}
	return colors
}
