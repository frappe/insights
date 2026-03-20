import { defineAsyncComponent } from 'vue'
import { __ } from '../translation'

const NumberTypes = ['Integer', 'Decimal']
const TextTypes = ['Text', 'String', 'JSON', 'Array']
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
	{ label: __('Auto'), value: 'Auto' },
	{ label: __('String'), value: 'String' },
	{ label: __('Text'), value: 'Text' },
	{ label: __('Integer'), value: 'Integer' },
	{ label: __('Decimal'), value: 'Decimal' },
	{ label: __('Date'), value: 'Date' },
	{ label: __('Time'), value: 'Time' },
	{ label: __('Datetime'), value: 'Datetime' },
	{ label: __('JSON'), value: 'JSON' },
	{ label: __('Array'), value: 'Array' },
] as const

export const FILTER_TYPES = ['String', 'Number', 'Date'] as const
export type FilterType = typeof FILTER_TYPES[number]

export const joinTypes = [
	{
		label: __('Inner'),
		icon: defineAsyncComponent(() => import('../components/Icons/JoinInnerIcon.vue')),
		value: 'inner',
		description: __('Keep only rows that have matching values in both tables'),
	},
	{
		label: __('Left'),
		icon: defineAsyncComponent(() => import('../components/Icons/JoinLeftIcon.vue')),
		value: 'left',
		description: __('Keep all existing rows and include matching rows from the new table'),
	},
	{
		label: __('Right'),
		icon: defineAsyncComponent(() => import('../components/Icons/JoinRightIcon.vue')),
		value: 'right',
		description:
			'Keep all rows from the new table and include matching rows from the existing table',
	},
	{
		label: __('Full'),
		icon: defineAsyncComponent(() => import('../components/Icons/JoinFullIcon.vue')),
		value: 'full',
		description: __('Keep all rows from both tables'),
	},
] as const


export const granularityOptions = [
	{ label: __('Second'), value: 'second' },
	{ label: __('Minute'), value: 'minute' },
	{ label: __('Hour'), value: 'hour' },
	{ label: __('Day'), value: 'day'},
	{ label: __('Week'), value: 'week'},
	{ label: __('Month'), value: 'month'},
	{ label: __('Quarter'), value: 'quarter'},
	{ label: __('Year'), value: 'year'},
	{ label: __('Fiscal Year'), value: 'fiscal_year'},
] as const

export type GranularityType = typeof granularityOptions[number]['value']
