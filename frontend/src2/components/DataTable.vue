<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { Plus, Search, Table2Icon } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import { usePagination } from '../composables/usePagination'
import { createHeaders, formatNumber, getShortNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import {
	applyDateRule,
	applyRankRule,
	applyRule,
	applyTextRule,
	cell_rules,
	date_rules,
	FormatGroupArgs,
	FormattingMode,
	garByPercentage,
	ragByPercentage,
	rank_rules,
	text_rules,
} from '../query/components/formatting_utils'
import { QueryResultColumn, QueryResultRow, SortDirection, SortOrder } from '../types/query.types'
import DataTableColumn from './DataTableColumn.vue'
import DataTableFooter from './DataTableFooter.vue'
import LazyTextInput from './LazyTextInput.vue'

const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
	showRowTotals?: boolean
	showColumnTotals?: boolean
	showFilterRow?: boolean
	enablePagination?: boolean
	enableColorScale?: boolean
	enableNewColumn?: boolean
	replaceNullsWithZeros?: boolean
	compactNumbers?: boolean
	loading?: boolean
	onExport?: Function
	downloading?: boolean
	formatGroup?: FormatGroupArgs
	sortOrder?: SortOrder
	onSortChange?: (column_name: string, direction: SortDirection) => void
	onColumnRename?: (column_name: string, new_name: string) => void
	onDrilldown?: (column: QueryResultColumn, row: QueryResultRow) => void
	stickyColumns?: string[]
	columnWidths?: Record<string, number>
	textWrap?: Record<string, boolean>
	pageSize?: number
	totalRowCount?: number
	onPageChange?: (page: number) => void
	currentPage?: number
	onFetchCount?: () => Promise<void> | void
	onFilterChange?: (filters: Record<string, string>) => void
}>()

const headers = computed(() => {
	if (!props.columns?.length) return []
	return createHeaders(props.columns)
})

const columnsMeta = computed(() => {
	if (!props.columns || !props.rows) return new Map()

	const meta = new Map()
	props.columns.forEach((col) => {
		const name = col.name
		const hasColorScaleFormatting = formattingRulesByColumn.value[name]?.some(
			(rule) => rule.mode === 'color_scale',
		)
		const metadata = {
			isNumber: FIELDTYPES.NUMBER.includes(col.type) || hasColorScaleFormatting,
		}

		meta.set(name, metadata)
	})
	return meta
})

const isNumberColumn = (col: string) => columnsMeta.value.get(col)?.isNumber
const isUrl = (value: any): boolean => {
	if (typeof value !== 'string') return false

	try {
		const url = new URL(value.trim())
		return url.protocol === 'http:' || url.protocol === 'https:'
	} catch {
		return false
	}
}

const $header = ref<HTMLElement>()
function getColumnWidth(column: string) {
	const cell = $header.value?.querySelector(`td[data-column-name="${column}"]`)
	if (cell && 'offsetWidth' in cell) {
		return cell.offsetWidth as number
	}
	return 200
}

const stickyColumnPositions = computed(() => {
	const columns = props.columns || []
	const stickyColumns = props.stickyColumns || []
	const positions: Record<string, string> = {}

	const indexColumnWidth = getColumnWidth('__index')

	let cumulativeWidth = indexColumnWidth

	const orderedStickyColumns = columns.filter((col) => stickyColumns.includes(col.name))

	orderedStickyColumns.forEach((col, index) => {
		positions[col.name] = `${cumulativeWidth}px`
		const headerWidth = getColumnWidth(col.name)
		cumulativeWidth += headerWidth
	})

	return positions
})

const isStickyColumn = (column: string) => {
	return props.stickyColumns?.includes(column)
}

const getStickyColumnStyle = (column: string) => {
	if (!isStickyColumn(column)) return {}
	return {
		left: stickyColumnPositions.value[column] || '48px',
	}
}

const getColumnWidthStyle = (column: string) => {
	const width = props.columnWidths?.[column]
	if (width) {
		return {
			width: `${width}px`,
			minWidth: `${width}px`,
			maxWidth: `${width}px`,
		}
	}
	return {
		maxWidth: '400px',
	}
}

const getTextWrapClass = (column: string) => {
	if (props.textWrap?.[column]) return ''
	return 'truncate'
}

const filterPerColumn = ref<Record<string, string>>({})
const visibleRows = computed(() => {
	const columns = props.columns
	const rows = props.rows
	if (!columns?.length || !rows?.length || !props.showFilterRow) return rows

	if (props.onFilterChange) return rows

	const filters = filterPerColumn.value
	return rows.filter((row) => {
		return Object.entries(filters).every(([col, filter]) => {
			if (!filter) return true
			const isNumber = isNumberColumn(col)
			const value = row[col]
			return applyFilter(value, isNumber, filter)
		})
	})
})

watch(
	filterPerColumn,
	(filters) => {
		props.onFilterChange?.(filters)
	},
	{ deep: true },
)

function applyFilter(value: any, isNumber: boolean, filter: string) {
	if (isNumber) {
		const operator = ['>', '<', '>=', '<=', '=', '!='].find((op) => filter.startsWith(op))
		if (operator) {
			const num = Number(filter.replace(operator, ''))
			switch (operator) {
				case '>':
					return Number(value) > num
				case '<':
					return Number(value) < num
				case '>=':
					return Number(value) >= num
				case '<=':
					return Number(value) <= num
				case '=':
					return Number(value) === num
				case '!=':
					return Number(value) !== num
			}
		}
	}
	return String(value).toLowerCase().includes(filter.toLowerCase())
}

const totalPerColumn = computed(() => {
	const columns = props.columns
	const rows = visibleRows.value
	if (!columns?.length || !rows?.length || !props.showColumnTotals) return

	const totals: Record<string, number> = {}
	columns.forEach((col) => {
		if (isNumberColumn(col.name)) {
			totals[col.name] = rows.reduce((acc, row) => acc + (row[col.name] as number), 0)
		}
	})
	return totals
})

const totalPerRow = computed(() => {
	const columns = props.columns
	const rows = visibleRows.value
	if (!columns?.length || !rows?.length || !props.showRowTotals) return

	const totals: Record<number, number> = {}
	rows.forEach((row, idx) => {
		totals[idx] = columns.reduce((acc, col) => {
			if (isNumberColumn(col.name)) {
				return acc + (row[col.name] as number)
			}
			return acc
		}, 0)
	})
	return totals
})

const totalColumnTotal = computed(() => {
	if (!props.showColumnTotals || !totalPerColumn.value) return
	return Object.values(totalPerColumn.value).reduce((acc, val) => acc + val, 0)
})

const pagination = usePagination({
	pageSize: computed(() => props.pageSize ?? 100),
	rowCount: computed(() => visibleRows.value?.length ?? 0),
	totalRowCount: computed(() => props.totalRowCount),
	currentPage: computed(() => props.currentPage),
	onPageChange: props.onPageChange,
	enabled: computed(() => Boolean(props.enablePagination)),
})

const colorByPercentage = {
	0: 'bg-white text-gray-900',
	10: 'bg-blue-100 text-blue-900',
	30: 'bg-blue-200 text-blue-900',
	60: 'bg-blue-300 text-blue-900',
	90: 'bg-blue-400 text-blue-900',
	100: 'bg-blue-500 text-white',
}

const colorByValues = computed(() => {
	const columns = props.columns
	const rows = visibleRows.value
	if (!columns?.length || !rows?.length) return []

	let uniqueValues = [] as number[]
	columns.forEach((col) => {
		if (isNumberColumn(col.name)) {
			rows.forEach((row) => {
				const value = Number(row[col.name])
				if (!uniqueValues.includes(value)) {
					uniqueValues.push(value)
				}
			})
		}
	})

	uniqueValues = uniqueValues.sort((a, b) => a - b)
	const max = uniqueValues[uniqueValues.length - 1]
	const uniqueValuesNormalized = uniqueValues.map((val) => Math.round((val / max) * 100))
	const _colorByValues: Record<number, string> = {}
	uniqueValuesNormalized.forEach((percentVal, index) => {
		for (const [percent, color] of Object.entries(colorByPercentage)) {
			if (percentVal <= Number(percent)) {
				_colorByValues[uniqueValues[index]] = color
				break
			}
		}
	})

	return _colorByValues
})

const formattingRulesByColumn = computed(() => {
	const { formats } = props.formatGroup || {}
	const columns = props.columns || []
	const result: Record<string, FormattingMode[]> = {}

	if (!formats?.length) return result

	// ibis generates pivot columns as {measure}___{dim_value1}___{dim_value2}...
	// so the measure name is always the first part
	const getMeasureName = (name: string) => (name.includes('___') ? name.split('___')[0] : name)

	formats.forEach((format) => {
		const target = 'column' in format ? format.column?.column_name : null
		if (!target) return

		// get matches (direct or pivot suffix)
		const matchedColumns = columns.filter((col) => {
			const measureName = getMeasureName(col.name)
			return measureName === target || col.name.endsWith(`___${target}`)
		})

		if (matchedColumns.length > 0) {
			matchedColumns.forEach((col) => {
				;(result[col.name] ??= []).push(format)
			})
		} else {
			// Only apply to numeric value columns
			// We skip index 0 since its the dimension/row header
			columns.forEach((col, idx) => {
				const isNumeric = FIELDTYPES.NUMBER.includes(col.type)
				if (idx > 0 && isNumeric) {
					;(result[col.name] ??= []).push(format)
				}
			})
		}
	})

	return result
})

function getColorClass(colorName: string): string {
	if (!colorName) return 'bg-gray-500'

	switch (colorName.toLowerCase()) {
		case 'red':
			return 'bg-[#d87373] text-white'
		case 'green':
			return 'bg-[#6DB678] text-white'
		case 'amber':
			return 'bg-[#F8D16E] text-black'
		default:
			return colorName.startsWith('bg-') ? colorName : 'bg-gray-500'
	}
}

const getColumnMinMax = (columnName: string) => {
	const colorScaleFormats = formattingRulesByColumn.value[columnName]?.filter(
		(rule) => rule.mode === 'color_scale',
	)

	if (!colorScaleFormats?.length) {
		const values =
			props.rows?.map((row) => Number(row[columnName])).filter((val) => !isNaN(val)) || []
		return {
			min: Math.min(...values),
			max: Math.max(...values),
		}
	}

	const scaleScope = colorScaleFormats[0].scaleScope || 'global'
	let columnsToConsider = [columnName]

	if (scaleScope === 'global') {
		// Find all columns that have the same color_scale format applied
		const allFormattedColumns = Object.keys(formattingRulesByColumn.value).filter((col) => {
			return formattingRulesByColumn.value[col]?.some((rule) => rule.mode === 'color_scale')
		})

		// Calculate global min/max across all columns to ensure consistent scaling.
		// this works on:
		// multi-value pivot:  [Status]___[Measure] (eg: Draft___sum_of_mrr)
		// single-pivot: [Dimension] (eg: Paid, Unpaid)
		// multi-pivot:  [Dim1]___[Dim2] (eg: INR___Draft, USD___Paid)
		if (allFormattedColumns.length > 1) {
			if (columnName.includes('___')) {
				const parts = columnName.split('___')
				const measureName = parts[parts.length - 1]

				const hasMultiValuePivot = allFormattedColumns.some((col) =>
					col.endsWith('___' + measureName),
				)

				if (hasMultiValuePivot) {
					// multi-value pivot: only include columns ending with the same measure
					columnsToConsider = allFormattedColumns.filter((col) =>
						col.endsWith('___' + measureName),
					)
				} else {
					// multi-column pivot: all formatted columns represent the same measure
					columnsToConsider = allFormattedColumns
				}
			} else {
				columnsToConsider = allFormattedColumns
			}
		}
	}

	const values: number[] = []
	columnsToConsider.forEach((col) => {
		const colValues =
			props.rows?.map((row) => Number(row[col])).filter((val) => !isNaN(val)) || []
		values.push(...colValues)
	})

	return {
		min: Math.min(...values),
		max: Math.max(...values),
	}
}

function getDefaultColorScaleClass(colName: string, val: any): string {
	if (props.enableColorScale && isNumberColumn(colName)) {
		const numVal = Number(val)
		if (!isNaN(numVal)) {
			const colorByValue = colorByValues.value as Record<number, string>
			if (colorByValue && colorByValue[numVal]) {
				return colorByValue[numVal]
			}
		}
	}
	return ''
}

function normalizeCellValue(colName: string, val: any) {
	if (isNumberColumn(colName) && (val === null || val === undefined)) {
		return 0
	}
	return val
}

function getHighlightClassFromRules(colName: string, val: any, rules: FormattingMode[]): string {
	for (const format of rules) {
		let isHighlighted = false
		let colorClass = ''

		const normalizedValue = normalizeCellValue(colName, val)

		if (format.mode === 'cell_rules' && format.operator && format.value !== undefined) {
			const rule = {
				column: colName,
				operator: format.operator,
				value: format.value,
				color: format.color,
				mode: 'cell_rules',
			} as unknown as cell_rules

			if (applyRule(normalizedValue, rule)) {
				isHighlighted = true
				colorClass = getColorClass(format.color as string)
			}
		} else if (format.mode === 'text_rules') {
			const textRule = format as text_rules
			if (applyTextRule(normalizedValue, textRule)) {
				isHighlighted = true
				colorClass = getColorClass(textRule.color)
			}
		} else if (format.mode === 'date_rules') {
			const dateRule = format as date_rules
			if (applyDateRule(normalizedValue, dateRule)) {
				isHighlighted = true
				colorClass = getColorClass(dateRule.color)
			}
		} else if (format.mode === 'rank_rules') {
			const rankRule = format as rank_rules
			const allColumnValues =
				props.rows?.map((row) => normalizeCellValue(colName, row[colName])) || []
			if (applyRankRule(normalizedValue, rankRule, allColumnValues)) {
				isHighlighted = true
				colorClass = getColorClass(rankRule.color)
			}
		}

		if (isHighlighted && colorClass) {
			return colorClass
		}
	}
	return ''
}

function getColorScaleClassFromFormat(colName: string, val: any, format: FormattingMode): string {
	if (format.mode !== 'color_scale') return ''
	const numVal = Number(val)
	if (isNaN(numVal)) return ''

	const { min, max } = getColumnMinMax(colName)
	let percentile: number = 0
	const normalizedValue = (numVal - min) / (max - min)
	percentile = Math.round(normalizedValue * 100)
	percentile = Math.max(0, Math.min(100, percentile))

	let colorScale: Record<string, string>
	if (format.colorScale) {
		format.colorScale == 'Red-Green'
			? (colorScale = ragByPercentage)
			: (colorScale = garByPercentage)
	} else {
		colorScale = ragByPercentage
	}

	const thresholds = Object.keys(colorScale)
		.map(Number)
		.sort((a, b) => a - b)

	let selectedThreshold = thresholds[0]
	for (const threshold of thresholds) {
		if (percentile >= threshold) {
			selectedThreshold = threshold
		}
	}
	const thresholdKey = String(selectedThreshold)
	const bgClass = colorScale[thresholdKey]?.trim() || 'bg-gray-300'
	return `${bgClass}`
}

function getColorScaleClassFromRules(colName: string, val: any, rules: FormattingMode[]): string {
	for (const format of rules) {
		if (format.mode === 'color_scale') {
			const cls = getColorScaleClassFromFormat(colName, val, format)
			if (cls) return cls
		}
	}
	return ''
}

function getCellStyleClass(colName: string, val: any): string {
	const defaultScale = getDefaultColorScaleClass(colName, val)
	if (defaultScale) return defaultScale

	const rules = formattingRulesByColumn.value[colName]
	if (!rules?.length) return ''

	const highlight = getHighlightClassFromRules(colName, val, rules)
	if (highlight) return highlight

	const scale = getColorScaleClassFromRules(colName, val, rules)
	if (scale) return scale

	return ''
}

function _formatNumber(value: any) {
	const isNull = value === null || value === undefined
	if (isNull) {
		return props.replaceNullsWithZeros ? 0 : 'null'
	}
	return props.compactNumbers ? getShortNumber(value) : formatNumber(value)
}

const showNewColumn = ref(false)
function toggleNewColumn() {
	showNewColumn.value = !showNewColumn.value
	// scroll towards the far right of the datatable
	nextTick(() => {
		if ($header.value) {
			const lastColumn = $header.value.querySelector('tr:last-child')
			if (lastColumn) {
				lastColumn.scrollIntoView({ behavior: 'smooth', inline: 'end' })
			}
		}
	})
}
</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="relative h-full w-full border-separate border-spacing-0">
				<thead ref="$header" class="sticky top-0 z-10 bg-gray-50">
					<tr v-for="headerRow in headers">
						<td
							class="sticky left-0 h-8 whitespace-nowrap border-b border-r bg-gray-50 px-3"
							data-column-name="__index"
							width="1px"
						></td>
						<td
							v-for="(header, idx) in headerRow"
							:key="idx"
							class="h-8 border-b border-r"
							:class="[
								header.isLast && isNumberColumn(header.column.name)
									? 'text-right'
									: 'text-left',
								isStickyColumn(header.column.name) ? 'sticky bg-gray-50' : '',
							]"
							:style="{
								...getStickyColumnStyle(header.column.name),
								...getColumnWidthStyle(header.column.name),
							}"
							:colspan="header.colspan"
							:data-column-name="header.column.name"
						>
							<DataTableColumn
								v-if="header.isLast"
								:label="header.label"
								:on-rename="
									props.onColumnRename
										? (newName) =>
												props.onColumnRename?.(header.column.name, newName)
										: undefined
								"
								:sort-order="props.sortOrder?.[header.column.name]"
								:on-sort-change="
									props.onSortChange
										? (direction) =>
												props.onSortChange?.(header.column.name, direction)
										: undefined
								"
							>
								<template #prefix>
									<slot name="header-prefix" :column="header.column" />
								</template>
								<template #suffix>
									<slot name="header-suffix" :column="header.column" />
								</template>
							</DataTableColumn>

							<div v-else class="flex items-center truncate px-2">
								{{ header.label }}
							</div>
						</td>

						<td v-if="props.enableNewColumn" class="h-8 border-b border-r">
							<Button
								v-if="!showNewColumn"
								variant="ghost"
								class="!min-w-10 !w-full"
								@click="toggleNewColumn"
							>
								<template #icon>
									<Plus class="size-4 text-gray-700" :stroke-width="1.5" />
								</template>
							</Button>
							<slot
								v-if="showNewColumn"
								name="new-column-editor"
								:toggle="toggleNewColumn"
							/>
						</td>

						<td
							v-if="props.showRowTotals"
							class="h-8 border-b border-r px-3 text-right"
							width="1px"
						>
							<div class="truncate pl-3 pr-20"></div>
						</td>
					</tr>

					<tr v-if="props.showFilterRow">
						<td
							class="sticky left-0 h-8 whitespace-nowrap border-b border-r bg-gray-50 px-3"
							width="1px"
						></td>
						<td
							v-for="(column, idx) in props.columns"
							:key="idx"
							class="h-8 border-b border-r p-1"
							:class="isStickyColumn(column.name) ? 'sticky bg-gray-50' : ''"
							:style="{
								...getStickyColumnStyle(column.name),
								...getColumnWidthStyle(column.name),
							}"
						>
							<LazyTextInput
								:model-value="filterPerColumn[column.name]"
								@update:model-value="
									(value) => (filterPerColumn[column.name] = value)
								"
								class="[&_input]:h-6 [&_input]:bg-gray-200/80"
							>
								<template #prefix>
									<Search class="size-3.5 text-gray-500" :stroke-width="1.5" />
								</template>
								<template #suffix>
									<LoadingIndicator
										v-if="props.loading"
										class="size-3.5 text-gray-500"
									/>
								</template>
							</LazyTextInput>
						</td>
						<td
							v-if="props.showRowTotals"
							class="border-b border-r px-3 text-right"
							width="1px"
						>
							<div class="truncate pl-3 pr-20"></div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(row, idx) in visibleRows?.slice(
							pagination.startIndex.value,
							pagination.endIndex.value,
						)"
						:key="idx"
					>
						<td
							class="tnum sticky left-0 h-8 whitespace-nowrap border-b border-r bg-white px-3 text-right text-xs"
							width="1px"
							height="30px"
						>
							{{ idx + pagination.rowDisplayOffset.value + 1 }}
						</td>

						<td
							v-for="col in props.columns"
							class="h-8 border-b border-r px-3 text-gray-800 leading-5 py-1.5"
							:class="[
								getTextWrapClass(col.name),
								isNumberColumn(col.name) ? 'tnum text-right' : 'text-left',
								props.enableColorScale && isNumberColumn(col.name)
									? colorByValues[row[col.name]]
									: '',
								isNumberColumn(col.name) && props.onDrilldown
									? 'cursor-pointer'
									: '',
								getCellStyleClass(col.name, row[col.name]),
								isStickyColumn(col.name) ? 'sticky bg-white' : '',
							]"
							:style="{
								...getStickyColumnStyle(col.name),
								...getColumnWidthStyle(col.name),
							}"
							height="30px"
							@dblclick="isNumberColumn(col.name) && props.onDrilldown?.(col, row)"
						>
							<template v-if="isNumberColumn(col.name)">
								{{ _formatNumber(row[col.name]) }}
							</template>
							<template v-else-if="isUrl(row[col.name])">
								<a :href="row[col.name]" target="_blank" class="underline">
									{{ row[col.name] }}
								</a>
							</template>

							<template v-else>
								{{ row[col.name] }}
							</template>
						</td>

						<td v-if="props.enableNewColumn" class="h-8 border-b border-r px-3"></td>

						<td
							v-if="props.showRowTotals && totalPerRow"
							class="tnum h-8 border-b border-r px-3 text-right font-bold"
						>
							{{ _formatNumber(totalPerRow[idx]) }}
						</td>
					</tr>

					<tr
						v-if="props.showColumnTotals && totalPerColumn"
						class="sticky bottom-0 border-b bg-white"
					>
						<td class="h-8 whitespace-nowrap border-r border-t px-3"></td>
						<td
							v-for="col in props.columns"
							class="h-8 truncate border-r border-t px-3 font-bold text-gray-800"
							:class="[
								isNumberColumn(col.name) ? 'tnum text-right' : 'text-left',
								isStickyColumn(col.name) ? 'sticky bg-white' : '',
							]"
							:style="{
								...getStickyColumnStyle(col.name),
								...getColumnWidthStyle(col.name),
							}"
						>
							{{
								isNumberColumn(col.name)
									? _formatNumber(totalPerColumn[col.name])
									: ''
							}}
						</td>

						<td
							v-if="props.showRowTotals && totalColumnTotal"
							class="tnum h-8 border-r border-t px-3 text-right font-bold"
						>
							{{ _formatNumber(totalColumnTotal) }}
						</td>
					</tr>

					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer">
			<DataTableFooter
				:pagination="props.enablePagination ? pagination : undefined"
				:total-row-count="props.totalRowCount"
				:on-fetch-count="props.onFetchCount"
				@prev="pagination.prev"
				@next="pagination.next"
			>
				<template #left>
					<slot name="footer-left" />
				</template>
				<template #actions>
					<slot name="footer-right-actions" />
				</template>
			</DataTableFooter>
		</slot>
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
			<p class="text-center text-gray-500">No data to display.</p>
		</div>
	</div>

	<div
		v-if="props.loading"
		class="absolute left-0 right-0 top-0 z-20 h-0.5 animate-pulse bg-blue-500"
	/>
</template>
