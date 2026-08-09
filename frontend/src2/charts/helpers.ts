import { FIELDTYPES } from '../helpers/constants'
import { AXIS_CHARTS, AxisChartConfig, ChartConfig } from '../types/chart.types'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'

// What a Chart's config needs doing to it before anything reads it. Drawing is
// not here: the adapter turns a config into chart props, and frappe-ui draws
// them.

// eslint-disable-next-line no-unused-vars
export function guessChart(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	// categorize the columns into dimensions and measures and then into discrete and continuous
	const dimensions = columns.filter((c) => FIELDTYPES.DIMENSION.includes(c.type))
	const discreteDimensions = dimensions.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousDimensions = dimensions.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	const measures = columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
	const discreteMeasures = measures.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousMeasures = measures.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	if (measures.length === 1 && dimensions.length === 0) return 'number'
	if (discreteDimensions.length === 1 && measures.length) return 'bar'
	if (continuousDimensions.length === 1 && measures.length) return 'line'
	if (discreteDimensions.length > 1 && measures.length) return 'table'
}

export function handleOldXAxisConfig(old_x_axis: any): AxisChartConfig['x_axis'] {
	if (old_x_axis && old_x_axis.column_name) {
		return {
			dimension: old_x_axis,
		}
	}
	return old_x_axis
}

export function handleOldYAxisConfig(old_y_axis: any): AxisChartConfig['y_axis'] {
	if (Array.isArray(old_y_axis)) {
		return {
			series: old_y_axis.map((measure: any) => ({ measure })),
		}
	}
	return old_y_axis
}

// Every chart type reads a fixed set of slots off the config, and the validator and the
// config forms reach into them without guarding. A type switch replaces the config
// wholesale, so the incoming type's slots have to exist before anything reads them.
export function ensureConfigSlots(config: any, chart_type: string) {
	if (AXIS_CHARTS.includes(chart_type)) {
		config.x_axis = config.x_axis || {}
		config.x_axis.dimension = config.x_axis.dimension || {}
		config.y_axis = config.y_axis || {}
		config.y_axis.series = config.y_axis.series || []
	}

	if (chart_type === 'Map') {
		config.location_column = config.location_column || {}
		config.value_column = config.value_column || {}
	}

	return config
}

export function setDimensionNames(config: any) {
	const setDimensionName = (dimension: any) => {
		if (
			dimension &&
			typeof dimension === 'object' &&
			!dimension.dimension_name &&
			dimension.column_name
		) {
			dimension.dimension_name = dimension.column_name
		}
		return dimension
	}

	if (config.x_axis?.dimension) {
		config.x_axis.dimension = setDimensionName(config.x_axis.dimension)
	}
	if (config.split_by?.dimension) {
		config.split_by.dimension = setDimensionName(config.split_by.dimension)
	}
	if (config.date_column) {
		config.date_column = setDimensionName(config.date_column)
	}
	if (config.label_column) {
		config.label_column = setDimensionName(config.label_column)
	}
	if (config.rows && config.rows.length) {
		config.rows = config.rows.map(setDimensionName)
	}
	if (config.columns && config.columns.length) {
		config.columns = config.columns.map(setDimensionName)
	}
	return config
}

// Every saved config passes through here before anything reads it: the slots are
// read without guarding, and a config saved by an older version may not have
// them. The chart store runs it on load, and the viewer endpoint's config runs it
// too — a card drawn on a desk page and the same card in the builder must not
// disagree about what an old chart looks like.
export function normalizeChartConfig(config: any, chart_type: string) {
	config.order_by = config.order_by || []
	config.limit = config.limit || 100

	if ('x_axis' in config && config.x_axis) {
		config.x_axis = handleOldXAxisConfig(config.x_axis)
	}
	if ('y_axis' in config && Array.isArray(config.y_axis)) {
		config.y_axis = handleOldYAxisConfig(config.y_axis)
	}
	if ('split_by' in config && config.split_by) {
		config.split_by = handleOldXAxisConfig(config.split_by)
	}
	if (chart_type === 'Funnel') {
		config.label_position = config.label_position || 'left'
	}
	if (chart_type === 'Donut') {
		config.legend_position = config.legend_position || 'bottom'
	}

	config = setDimensionNames(config)
	config = ensureConfigSlots(config, chart_type)
	return config
}

export function getGranularity(dimension_name: string, config: ChartConfig) {
	if ('x_axis' in config && config.x_axis.dimension.dimension_name === dimension_name) {
		return config.x_axis.dimension.granularity
	}

	if ('split_by' in config && config.split_by?.dimension?.dimension_name === dimension_name) {
		return config.split_by.dimension.granularity
	}

	if ('date_column' in config && config.date_column?.dimension_name === dimension_name) {
		return config.date_column.granularity
	}

	if ('label_column' in config && config.label_column?.dimension_name === dimension_name) {
		return config.label_column.granularity
	}

	if ('rows' in config) {
		const row = config.rows.find((r: any) => r.dimension_name === dimension_name)
		if (row) return row.granularity
	}

	if ('columns' in config) {
		const column = config.columns.find((c: any) => c.dimension_name === dimension_name)
		if (column) return column.granularity
	}
}
