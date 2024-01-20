export const NEW_COLUMN = {
	table: '',
	column: '',
	label: '',
	type: '',
	alias: '',
	order: '',
	granularity: '',
	aggregation: '',
	format: {},
	expression: {},
}

export const NEW_FILTER = {
	column: { ...NEW_COLUMN },
	operator: {},
	value: {},
	expression: {},
}

export const NEW_JOIN = {
	join_type: { label: 'Inner Join', value: 'inner' },
	left_table: {},
	left_column: {},
	right_table: {},
	right_column: {},
}

export const NEW_TRANSFORM = {
	type: '',
	options: {},
}
