import { defineAsyncComponent } from 'vue'

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

export const joinTypes = [
	{
		label: 'Inner',
		icon: defineAsyncComponent(() => import('../components/Icons/JoinInnerIcon.vue')),
		value: 'inner',
		description: 'Keep only rows that have matching values in both tables',
	},
	{
		label: 'Left',
		icon: defineAsyncComponent(() => import('../components/Icons/JoinLeftIcon.vue')),
		value: 'left',
		description: 'Keep all existing rows and include matching rows from the new table',
	},
	{
		label: 'Right',
		icon: defineAsyncComponent(() => import('../components/Icons/JoinRightIcon.vue')),
		value: 'right',
		description:
			'Keep all rows from the new table and include matching rows from the existing table',
	},
	{
		label: 'Full',
		icon: defineAsyncComponent(() => import('../components/Icons/JoinFullIcon.vue')),
		value: 'full',
		description: 'Keep all rows from both tables',
	},
] as const
