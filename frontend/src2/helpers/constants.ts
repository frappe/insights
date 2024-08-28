const NumberTypes = ['Integer', 'Decimal']
const TextTypes = ['Text', 'String']
const DateTypes = ['Date', 'Datetime', 'Time']

export const FIELDTYPES = {
	NUMBER: NumberTypes,
	TEXT: TextTypes,
	DATE: DateTypes,
	MEASURE: NumberTypes,
	DIMENSION: TextTypes.concat(DateTypes),
	DISCRETE: TextTypes,
	CONTINUOUS: NumberTypes.concat(DateTypes),
}

export const COLUMN_TYPES = [
	{ label: 'String', value: 'String' },
	{ label: 'Text', value: 'Text' },
	{ label: 'Integer', value: 'Integer' },
	{ label: 'Decimal', value: 'Decimal' },
	{ label: 'Date', value: 'Date' },
	{ label: 'Time', value: 'Time' },
	{ label: 'Datetime', value: 'Datetime' },
]
