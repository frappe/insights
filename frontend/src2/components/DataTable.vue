<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { useChartTokens } from 'frappe-ui/charts'
import { ExternalLink, Plus, Table2Icon } from 'lucide-vue-next'
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { usePagination } from '../composables/usePagination'
import { createHeaders } from '../helpers'
import { carriedCurrency, numberFormatter, type NumberFormatter } from '../charts/number_format'
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
	rank_rules,
	rulesByColumn,
	text_rules,
} from '../query/components/formatting_utils'
import {
	colorScaleDirection,
	deepEnd,
	type ColorScaleDirection,
	fillAt,
	magnitudeScale,
	statusFill,
	type CellFill,
} from '../query/components/formatting_colors'
import { NumberFormat } from '../types/chart.types'
import {
	DataFormat,
	QueryResultColumn,
	QueryResultRow,
	SortDirection,
	SortOrder,
} from '../types/query.types'
import { RESULT_GRID_HOST } from './result_pane/result_grid'
import DataTableColumn from './DataTableColumn.vue'
import DataTableFooter from './DataTableFooter.vue'

const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
	showRowTotals?: boolean
	showColumnTotals?: boolean
	enableColorScale?: boolean
	enableNewColumn?: boolean
	replaceNullsWithZeros?: boolean
	loading?: boolean
	filtering?: boolean
	formatGroup?: FormatGroupArgs
	sortOrder?: SortOrder
	onSortChange?: (column_name: string, direction: SortDirection) => void
	onColumnRename?: (column_name: string, new_name: string) => void
	// the event too: a caller that opens a menu at the click needs the point, and
	// the cell is the only thing that knows where it was
	onDrilldown?: (column: QueryResultColumn, row: QueryResultRow, event: MouseEvent) => void
	// where a cell's value points, when it points anywhere. The table draws the
	// link and knows nothing about what is behind it
	cellLink?: (column: QueryResultColumn, row: QueryResultRow) => string | undefined
	stickyColumns?: string[]
	columnWidths?: Record<string, number>
	textWrap?: Record<string, boolean>
	columnFormats?: Record<string, DataFormat>
	/** How every cell prints, before a column says otherwise. */
	numberFormat?: NumberFormat
	/** How one column prints, by name. Overrides `numberFormat` key by key. */
	numberFormats?: Record<string, NumberFormat>
	pageSize?: number
	currentPage?: number
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

const linkOf = (col: QueryResultColumn, row: QueryResultRow): string | undefined => {
	const href = props.cellLink?.(col, row)
	if (href) return href
	return isUrl(row[col.name]) ? String(row[col.name]).trim() : undefined
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

const totalPerColumn = computed(() => {
	const columns = props.columns
	const rows = props.rows
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
	const rows = props.rows
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

// The cursor is the host's: a pane above passes the page down and slices the
// rows itself. What is left here is the row gutter: `rowDisplayOffset` is what
// makes row 1 of page 3 print as 201.
const pagination = usePagination({
	pageSize: computed(() => props.pageSize ?? 100),
	rowCount: computed(() => props.rows?.length ?? 0),
	currentPage: computed(() => props.currentPage),
})

// The grid draws in the same colors every chart does, so a scale reads the
// same whether it is a heatmap or a column of numbers. `useChartTokens`
// re-resolves when the theme flips.
const $root = ref<HTMLElement>()
const { tokens } = useChartTokens($root)

// Built once per theme rather than per cell: every cell in a column reads the
// same scale, and a grid asks for it thousands of times. The chart-wide toggle
// and a column's own rule draw from the same two, so they cannot disagree.
const scales = computed(() => ({
	ascending: magnitudeScale(tokens.value, 'ascending'),
	descending: magnitudeScale(tokens.value, 'descending'),
}))

const formattingRulesByColumn = computed(() =>
	rulesByColumn(
		props.formatGroup?.formats,
		(props.columns || []).map((col) => col.name),
	),
)

// Every column's values, read once per grid: a scale and a rank rule both ask
// for them per cell, and a grid has thousands of cells. They are the rows the
// grid draws.
const columnValues = computed(() => {
	const values: Record<string, any[]> = {}
	const rows = props.rows || []
	for (const column of props.columns || []) {
		values[column.name] = rows.map((row) => row[column.name])
	}
	return values
})

function valuesOf(columnName: string): any[] {
	return columnValues.value[columnName] ?? (props.rows || []).map((row) => row[columnName])
}

function numbersOf(columnName: string): number[] {
	return valuesOf(columnName)
		.map((value) => Number(value))
		.filter((value) => !isNaN(value))
}

const getColumnMinMax = (columnName: string) => {
	const colorScaleFormats = formattingRulesByColumn.value[columnName]?.filter(
		(rule) => rule.mode === 'color_scale',
	)

	if (!colorScaleFormats?.length) {
		const values = numbersOf(columnName)
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
	columnsToConsider.forEach((col) => values.push(...numbersOf(col)))

	return {
		min: Math.min(...values),
		max: Math.max(...values),
	}
}

// A cell asks for its column's range, and a grid has thousands of them, so the
// walk happens once per column and not once per cell.
const columnRanges = computed(() => {
	const ranges: Record<string, { min: number; max: number }> = {}
	for (const column of props.columns || []) {
		if (isNumberColumn(column.name)) ranges[column.name] = getColumnMinMax(column.name)
	}
	return ranges
})

function getDefaultColorScaleFill(colName: string, val: any): CellFill | undefined {
	if (!props.enableColorScale || !isNumberColumn(colName)) return undefined
	return columnScaleFill(colName, val, 'ascending')
}

/**
 * Where a value sits in its own column, as a stop on the scale. The chart-wide
 * toggle and a column's own rule both rank through this, so the same cell is
 * never painted by two calculations.
 */
function columnScaleFill(
	colName: string,
	val: any,
	direction: ColorScaleDirection,
): CellFill | undefined {
	const numVal = Number(val)
	if (isNaN(numVal)) return undefined

	const { min, max } = columnRanges.value[colName] ?? getColumnMinMax(colName)
	// A column of zeros states no magnitude, so it is left unpainted rather than
	// painted as its own maximum.
	if (max === min && min === 0) return undefined
	// A column with one value has no range to rank against, so every cell reads
	// as the scale's deep end, which is the end the direction puts it at.
	const percentile =
		max === min ? deepEnd(direction) : Math.round(((numVal - min) / (max - min)) * 100)

	return fillAt(scales.value[direction], percentile)
}

function normalizeCellValue(colName: string, val: any) {
	if (isNumberColumn(colName) && (val === null || val === undefined)) {
		return 0
	}
	return val
}

/** The color the first matching rule asks for, if any rule matches. */
function matchedRuleColor(colName: string, val: any, rules: FormattingMode[]): string | undefined {
	const value = normalizeCellValue(colName, val)

	for (const format of rules) {
		if (format.mode === 'cell_rules' && format.operator && format.value !== undefined) {
			const rule = { ...format, column: colName } as unknown as cell_rules
			if (applyRule(value, rule)) return format.color
		} else if (format.mode === 'text_rules') {
			if (applyTextRule(value, format as text_rules)) return format.color
		} else if (format.mode === 'date_rules') {
			if (applyDateRule(value, format as date_rules)) return format.color
		} else if (format.mode === 'rank_rules') {
			const allColumnValues = valuesOf(colName).map((value) =>
				normalizeCellValue(colName, value),
			)
			if (applyRankRule(value, format as rank_rules, allColumnValues)) return format.color
		}
	}
	return undefined
}

function getColorScaleFillFromFormat(
	colName: string,
	val: any,
	format: FormattingMode,
): CellFill | undefined {
	if (format.mode !== 'color_scale') return undefined
	return columnScaleFill(colName, val, colorScaleDirection(format.colorScale))
}

function getColorScaleFillFromRules(
	colName: string,
	val: any,
	rules: FormattingMode[],
): CellFill | undefined {
	for (const format of rules) {
		if (format.mode === 'color_scale') {
			const fill = getColorScaleFillFromFormat(colName, val, format)
			if (fill) return fill
		}
	}
	return undefined
}

type CellPaint = Partial<CellFill> & { borderColor?: string }

/**
 * A filled cell draws its gridline in its own fill. The table's border is an
 * outline gray that separates two bare cells, and any other color over a fill
 * still cuts the block. Painting the border in the fill keeps the cell edge
 * where it was, so nothing reflows, and a run of filled cells reads as one block.
 */
function paint(fill: CellFill): CellPaint {
	return { ...fill, borderColor: fill.backgroundColor }
}

/**
 * What paints a cell. A rule verdict is a semantic class, a scale stop is a
 * resolved color, and one call hands back whichever applies so the cell binds
 * both the same way. A cell that nothing paints keeps the table's own grid.
 */
function getCellPaint(colName: string, val: any): CellPaint {
	const defaultScale = getDefaultColorScaleFill(colName, val)
	if (defaultScale) return paint(defaultScale)

	const rules = formattingRulesByColumn.value[colName]
	if (!rules?.length) return {}

	const ruleColor = matchedRuleColor(colName, val, rules)
	if (ruleColor) return paint(statusFill(ruleColor, tokens.value))

	const scale = getColorScaleFillFromRules(colName, val, rules)
	if (scale) return paint(scale)

	return {}
}

// The grid formats its cells the way every chart does: it states the policy and
// the one resolver answers it. A column is looked up by name, which is what the
// Measure behind it is called. A cell reads its currency off its own row, and a
// column total off every row it sums, so a total over rows in different
// currencies prints bare. A row total belongs to no column and prints under the
// table's own default.
const cellFormatters = computed(() => {
	const config = { number_format: props.numberFormat, number_formats: props.numberFormats }
	const formats = props.columnFormats || {}
	const rows = props.rows || []
	const cache = new Map<string, NumberFormatter>()
	return (columnName: string, row?: QueryResultRow): NumberFormatter => {
		const over = row ? [row] : rows
		const key = `${columnName}\0${carriedCurrency(over, columnName)}`
		let format = cache.get(key)
		if (!format) {
			format = numberFormatter(
				config,
				{ measure_name: columnName, format: formats[columnName] },
				over,
			)
			cache.set(key, format)
		}
		return format
	}
})

const defaultFormatter = computed(() => numberFormatter(props.numberFormat))

function _formatNumber(value: any, columnName?: string, row?: QueryResultRow) {
	const format = columnName ? cellFormatters.value(columnName, row) : defaultFormatter.value
	const isNull = value === null || value === undefined
	// A zero standing in for a missing number is still a number of this column,
	// so it prints in the column's own units.
	if (isNull) {
		return props.replaceNullsWithZeros ? format(0) : 'null'
	}
	return format(value)
}

/**
 * Bring a column into view and mark it for a moment.
 *
 * The pane around the grid owns the find and asks for this. The grid owns where
 * a column sits, which is why the pane asks rather than reaching for the cell
 * itself. A grid drawn outside a pane registers with nobody and is never asked.
 */
function scrollToColumn(column_name: string) {
	nextTick(() => {
		const cell = $root.value?.querySelector(
			`td[data-column-name="${column_name}"]`,
		) as HTMLElement | null
		if (!cell) return
		cell.scrollIntoView({ inline: 'center', block: 'nearest' })
		cell.classList.add('bg-surface-gray-3')
		setTimeout(() => cell.classList.remove('bg-surface-gray-3'), 600)
	})
}

const pane = inject(RESULT_GRID_HOST, null)
onMounted(() => pane?.setGrid({ scrollToColumn }))
onBeforeUnmount(() => pane?.setGrid(undefined))

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
		ref="$root"
		class="flex h-full w-full flex-col overflow-hidden text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="relative h-full w-full border-separate border-spacing-0">
				<thead ref="$header" class="sticky top-0 z-10 bg-surface-gray-1">
					<tr v-for="headerRow in headers">
						<td
							class="sticky left-0 z-[1] h-8 whitespace-nowrap border-b border-r bg-surface-gray-1 px-3"
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
								isStickyColumn(header.column.name)
									? 'sticky z-[1] bg-surface-gray-1'
									: '',
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
									<Plus class="size-4 text-ink-gray-6" :stroke-width="1.5" />
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
				</thead>
				<tbody
					:class="
						props.filtering ? 'opacity-60 transition-opacity' : 'transition-opacity'
					"
				>
					<tr
						v-for="(row, idx) in props.rows?.slice(0, pagination.endIndex.value)"
						:key="idx"
					>
						<td
							class="tnum sticky left-0 z-[1] h-8 whitespace-nowrap border-b border-r bg-surface-base px-3 text-right text-xs"
							width="1px"
							height="30px"
						>
							{{ idx + pagination.rowDisplayOffset.value + 1 }}
						</td>

						<td
							v-for="col in props.columns"
							class="group/cell h-8 border-b border-r px-3 text-ink-gray-7 leading-5 py-1.5"
							:class="[
								getTextWrapClass(col.name),
								isNumberColumn(col.name) ? 'tnum text-right' : 'text-left',
								isNumberColumn(col.name) && props.onDrilldown
									? 'cursor-pointer'
									: '',
								isStickyColumn(col.name) ? 'sticky z-[1] bg-surface-base' : '',
							]"
							:style="{
								...getStickyColumnStyle(col.name),
								...getColumnWidthStyle(col.name),
								...getCellPaint(col.name, row[col.name]),
							}"
							height="30px"
							@dblclick="
								isNumberColumn(col.name) && props.onDrilldown?.(col, row, $event)
							"
						>
							<template v-if="isNumberColumn(col.name)">
								{{ _formatNumber(row[col.name], col.name, row) }}
							</template>
							<!-- the whole value is the control, so a link needs no column
							     of its own. The icon marks the one that leaves, and it
							     is drawn only under the pointer: a column where every
							     row links would otherwise be a column of icons. Its
							     space is held either way, so nothing shifts on hover.

							     The cell is what is pointed at, not the text: a value
							     short of the column's width would otherwise leave the
							     icon out of reach of most of the cell. The group is
							     named for it, because a card names a hover group of
							     its own around the whole table and a bare
							     `group-hover` answers whichever ancestor carries the
							     class. -->
							<a
								v-else-if="linkOf(col, row)"
								:href="linkOf(col, row)"
								target="_blank"
								rel="noopener noreferrer"
								class="inline-flex max-w-full items-center gap-1 hover:underline"
							>
								<span class="truncate">{{ row[col.name] }}</span>
								<ExternalLink
									class="size-3 shrink-0 text-ink-gray-5 opacity-0 transition-opacity group-hover/cell:opacity-100"
									stroke-width="1.5"
								/>
							</a>

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

					<!-- The cells carry the closing rule, not the row: under
					     `border-separate` a border on a `tr` is never painted. -->
					<tr
						v-if="props.showColumnTotals && totalPerColumn"
						class="sticky bottom-0 bg-surface-base"
					>
						<td class="h-8 whitespace-nowrap border-b border-r border-t px-3"></td>
						<td
							v-for="col in props.columns"
							class="h-8 truncate border-b border-r border-t px-3 font-bold text-ink-gray-7"
							:class="[
								isNumberColumn(col.name) ? 'tnum text-right' : 'text-left',
								isStickyColumn(col.name) ? 'sticky z-[1] bg-surface-base' : '',
							]"
							:style="{
								...getStickyColumnStyle(col.name),
								...getColumnWidthStyle(col.name),
							}"
						>
							{{
								isNumberColumn(col.name)
									? _formatNumber(totalPerColumn[col.name], col.name)
									: ''
							}}
						</td>

						<td
							v-if="props.showRowTotals && totalColumnTotal"
							class="tnum h-8 border-b border-r border-t px-3 text-right font-bold"
						>
							{{ _formatNumber(totalColumnTotal) }}
						</td>
					</tr>

					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer">
			<DataTableFooter>
				<template v-if="$slots['footer-left']" #left>
					<slot name="footer-left" />
				</template>
			</DataTableFooter>
		</slot>
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-ink-gray-2" stroke-width="1.5" />
			<p class="text-center text-ink-gray-4">No data to display.</p>
		</div>
	</div>

	<div
		v-if="props.loading && !props.filtering"
		class="absolute inset-0 flex items-center justify-center rounded-4 bg-surface-base/30 backdrop-blur-sm"
	>
		<LoadingIndicator class="h-5 w-5 text-ink-gray-4" />
	</div>
</template>
