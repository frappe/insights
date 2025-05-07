<script setup lang="ts">
import { Rating } from 'frappe-ui'
import { ChevronLeft, ChevronRight, Download, Search, Table2Icon } from 'lucide-vue-next'
import { computed, reactive, ref, watch } from 'vue'
import { createHeaders, formatNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { QueryResultColumn, QueryResultRow, SortDirection, SortOrder } from '../types/query.types'
import DataTableColumn from './DataTableColumn.vue'
import { applyRule, cell_rules, FormatGroupArgs, FormattingMode, garByPercentage, ragByPercentage } from '../query/components/formatting_utils'
import { useFormatStore } from '../stores/formatStore'

const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
	showRowTotals?: boolean
	showColumnTotals?: boolean
	showFilterRow?: boolean
	enablePagination?: boolean
	enableColorScale?: boolean
	loading?: boolean
  formatGroup?: FormatGroupArgs;
	onExport?: Function
	sortOrder?: SortOrder
	onSortChange?: (column_name: string, direction: SortDirection) => void
	onColumnRename?: (column_name: string, new_name: string) => void
	onDrilldown?: (column: QueryResultColumn, row: QueryResultRow) => void
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
		const metadata = {
			isNumber: FIELDTYPES.NUMBER.includes(col.type),
			isStarRating: false,
		}

		const values = props.rows!.map((row) => row[name])

		// Check if it's a star rating column
		if (
			metadata.isNumber &&
			(col.name.toLowerCase().includes('rating') || col.name.toLowerCase().includes('stars'))
		) {
			metadata.isStarRating = values.every((val) => val >= 0 && val <= 1)
		}

		meta.set(name, metadata)
	})
	return meta
})

const isNumberColumn = (col: string) => columnsMeta.value.get(col)?.isNumber
const isStarRating = (col: string) => columnsMeta.value.get(col)?.isStarRating
const isUrl = (value: any): boolean => typeof value === 'string' && value.startsWith('http')

const filterPerColumn = ref<Record<string, string>>({})
const visibleRows = computed(() => {
	const columns = props.columns
	const rows = props.rows
	if (!columns?.length || !rows?.length || !props.showFilterRow) return rows

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

const page = reactive({
	current: 1,
	size: 100,
	total: 1,
	startIndex: 0,
	endIndex: 99,
	next() {
		if (page.current < page.total) {
			page.current++
		}
	},
	prev() {
		if (page.current > 1) {
			page.current--
		}
	},
})
// @ts-ignore
page.total = computed(() => {
	if (!visibleRows.value?.length) return 1
	return Math.ceil(visibleRows.value.length / page.size)
})
// @ts-ignore
page.startIndex = computed(() => (page.current - 1) * page.size)
// @ts-ignore
page.endIndex = computed(() => Math.min(page.current * page.size, visibleRows.value?.length || 0))

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


const formatStore = useFormatStore();

watch(
  () => props.formatGroup,
  (newFormatGroup) => {
    if (newFormatGroup) {
      formatStore.setFormatting(newFormatGroup);
    }
  },
  { immediate: true },
);

const formattingRulesByColumn = computed(() => {
  const formatGroup = formatStore.conditionalFormatting;
  const result: Record<string, FormattingMode[]> = {};

  if (formatGroup?.formats?.length) {
    formatGroup.formats.forEach((format) => {
      if ("column" in format && format.column?.column_name) {
        const columnName = format.column.column_name;
        if (!result[columnName]) {
          result[columnName] = [];
        }
        result[columnName].push(format);
      }
    });
  }

  return result;
});

// get tailwind class bg
function getColorClass(colorName: string): string {
  if (!colorName) return "bg-gray-500";

  switch (colorName.toLowerCase()) {
    case "red":
      return "bg-[#FC7474] text-black";
    case "green":
      return "bg-[#58C08E] text-white";
    case "amber":
      return "bg-[#F8D16E] text-black";
    default:
      return colorName.startsWith("bg-") ? colorName : "bg-gray-500";
  }
}

function getCellStyleClass(colName: string, val: any): string {
  // first check if we should apply default color scale

  if (props.enableColorScale && isNumberColumn(colName)) {
    const numVal = Number(val);

    if (!isNaN(numVal)) {
      const colorByValue = colorByValues.value;

      if (colorByValue && colorByValue[numVal]) {
        return colorByValue[numVal];
      }
    }
  }

  // get formatting rules for the given column

  const rules = formattingRulesByColumn.value[colName];

  if (!rules?.length) return "";

  for (const format of rules) {

    if (
      format.mode === "cell_rules" &&
      format.operator &&
      format.value !== undefined
    ) {
      // check if the rule applies to this cell

      const rule = {
        column: colName,

        operator: format.operator,

        value: format.value,

        color: format.color,

        mode: "cell_rules",
      } as unknown as cell_rules;

      //highlight cells based on rule
      if (applyRule(val, rule)) {
        const colorClass = getColorClass(format.color as string);

        return `${colorClass}  `;
      }
    }
  }

  for (const format of rules) {
    if (format.mode === "color_scale") {
      const numVal = Number(val);
      if (isNaN(numVal)) {
        continue;
      }
      const allValues =
        props.rows

          ?.map((row) => Number(row[colName]))

          ?.filter((v) => !isNaN(v)) || [];
      if (!allValues.length) {
        continue;
      }
      const max = Math.max(...allValues);
      const percentage = Math.round((numVal / max) * 100);

      let colorScale;

      if (format.colorScale) {
        format.colorScale == "RAG"
          ? (colorScale = garByPercentage)
          : (colorScale = ragByPercentage);
      } else {
        colorScale = ragByPercentage;
      }
      const thresholds = Object.keys(colorScale)
        .map(Number)
        .sort((a, b) => a - b);
        
        //apply color based on threshold
      let selectedThreshold = thresholds[0];
      for (const threshold of thresholds) {
        if (percentage >= threshold) {
          selectedThreshold = threshold;
        } else {
          break;
        }
      }
      const thresholdKey = String(selectedThreshold);

      const bgClass = colorScale[thresholdKey]?.trim() || "bg-gray-300";

      return `${bgClass}  `;
    }
  }

  return "";
}


</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="relative h-full w-full border-separate border-spacing-0">
				<thead class="sticky top-0 z-10 bg-gray-50">
					<tr v-for="headerRow in headers">
						<td
							class="sticky left-0 z-10 h-8 whitespace-nowrap border-b border-r bg-gray-50 px-3"
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
							]"
							:colspan="header.colspan"
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
							class="sticky left-0 z-10 h-8 whitespace-nowrap border-b border-r bg-gray-50 px-3"
							width="1px"
						></td>
						<td
							v-for="(column, idx) in props.columns"
							:key="idx"
							class="h-8 border-b border-r p-1"
						>
							<FormControl
								type="text"
								v-model="filterPerColumn[column.name]"
								autocomplete="off"
								class="[&_input]:h-6 [&_input]:bg-gray-200/80"
							>
								<template #prefix>
									<Search class="h-4 w-4 text-gray-500" stroke-width="1.5" />
								</template>
							</FormControl>
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
						v-for="(row, idx) in visibleRows?.slice(page.startIndex, page.endIndex)"
						:key="idx"
					>
						<td
							class="tnum z-1 sticky left-0 h-8 whitespace-nowrap border-b border-r bg-white px-3 text-right text-xs"
							width="1px"
							height="30px"
						>
							{{ idx + page.startIndex + 1 }}
						</td>

						<td
							v-for="col in props.columns"
							class="h-8 max-w-[24rem] truncate border-b border-r px-3 text-gray-800"
							:class="[
								isNumberColumn(col.name) ? 'tnum text-right' : 'text-left',
								props.enableColorScale && isNumberColumn(col.name)
									? colorByValues[row[col.name]]
									: '',
								isNumberColumn(col.name) && props.onDrilldown
									? 'cursor-pointer'
									: '',
                  getCellStyleClass(col.name, row[col.name]),
							]"
							height="30px"
							@dblclick="isNumberColumn(col.name) && props.onDrilldown?.(col, row)"
						>
							<template v-if="isStarRating(col.name)">
								<Rating :modelValue="row[col.name] * 5" :readonly="true" />
							</template>
							<template v-else-if="isNumberColumn(col.name)">
								{{ formatNumber(row[col.name]) }}
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

						<td
							v-if="props.showRowTotals && totalPerRow"
							class="tnum h-8 border-b border-r px-3 text-right font-bold"
						>
							{{ formatNumber(totalPerRow[idx]) }}
						</td>
					</tr>

					<tr
						v-if="props.showColumnTotals && totalPerColumn"
						class="sticky bottom-0 z-10 border-b bg-white"
					>
						<td class="h-8 whitespace-nowrap border-r border-t px-3"></td>
						<td
							v-for="col in props.columns"
							class="h-8 truncate border-r border-t px-3 font-bold text-gray-800"
							:class="isNumberColumn(col.name) ? 'tnum text-right' : 'text-left'"
						>
							{{
								isNumberColumn(col.name)
									? formatNumber(totalPerColumn[col.name])
									: ''
							}}
						</td>

						<td
							v-if="props.showRowTotals && totalColumnTotal"
							class="tnum h-8 border-r border-t px-3 text-right font-bold"
						>
							{{ formatNumber(totalColumnTotal) }}
						</td>
					</tr>

					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer">
			<div class="flex flex-shrink-0 items-center justify-between border-t px-2 py-1">
				<slot name="footer-left">
					<div></div>
				</slot>
				<slot name="footer-right">
					<div class="flex items-center gap-2">
						<div
							v-if="props.enablePagination && visibleRows?.length && page.total > 1"
							class="flex flex-shrink-0 items-center justify-end gap-2"
						>
							<p class="tnum text-sm text-gray-600">
								{{ page.startIndex + 1 }} - {{ page.endIndex }} of
								{{ visibleRows.length }}
							</p>

							<div class="flex gap-2">
								<Button
									variant="ghost"
									@click="page.prev"
									:disabled="page.current === 1"
								>
									<ChevronLeft class="h-4 w-4 text-gray-700" stroke-width="1.5" />
								</Button>
								<Button
									variant="ghost"
									@click="page.next"
									:disabled="page.current === page.total"
								>
									<ChevronRight
										class="h-4 w-4 text-gray-700"
										stroke-width="1.5"
									/>
								</Button>
							</div>
						</div>
						<slot name="footer-right-actions"></slot>
						<Button v-if="props.onExport" variant="ghost" @click="props.onExport">
							<template #icon>
								<Download class="h-4 w-4 text-gray-700" stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</slot>
			</div>
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
		class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-white/30 backdrop-blur-sm"
	>
		<LoadingIndicator class="h-8 w-8 text-gray-700" />
	</div>
</template>