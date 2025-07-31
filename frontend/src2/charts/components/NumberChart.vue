<script setup lang="ts">
import { computed } from 'vue'
import { formatNumber, getShortNumber } from '../../helpers'
import { NumberChartConfig, NumberColumnOptions } from '../../types/chart.types'
import { QueryResult, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import Sparkline from './Sparkline.vue'

const props = defineProps<{
	config: NumberChartConfig
	result: QueryResult
}>()

const emit = defineEmits<{
	drillDown: [column: QueryResultColumn, row: QueryResultRow]
}>()

const config = computed(() => props.config)

const numberColumns = computed(() => {
	return config.value.number_columns.filter((c) => c.measure_name).map((c) => c.measure_name)
})
const dateValues = computed(() => {
	if (!config.value.date_column) return []
	const date_column = config.value.date_column.column_name
	return props.result.rows.map((row: any) => row[date_column])
})
const numberValuesPerColumn = computed(() => {
	if (!config.value.number_columns?.length) return {}
	if (!props.result?.columns.length) return {}

	return numberColumns.value.reduce((acc: any, measure_name: string) => {
		acc[measure_name] = props.result.rows.map((row: any) => row[measure_name])
		return acc
	}, {})
})

const cards = computed(() => {
	if (!config.value.number_columns?.length) return []
	if (!props.result?.columns.length) return []
	if (!Object.keys(numberValuesPerColumn.value).length) return []

	return numberColumns.value.map((measure_name: string, idx: number) => {
		const numberValues = numberValuesPerColumn.value[measure_name]
		const currentValue = numberValues[numberValues.length - 1] || 0
		const previousValue = numberValues[numberValues.length - 2] || 0
		const delta = config.value.negative_is_better
			? previousValue - currentValue
			: currentValue - previousValue
		const percentDelta = (delta / Math.abs(previousValue)) * 100

		const prefix = getNumberOption(idx, 'prefix')
		const suffix = getNumberOption(idx, 'suffix')
		const decimal = getNumberOption(idx, 'decimal')
		const shorten_numbers = getNumberOption(idx, 'shorten_numbers')

		return {
			measure_name,
			values: numberValues,
			currentValue: getFormattedValue(currentValue, decimal, shorten_numbers),
			previousValue: getFormattedValue(previousValue, decimal, shorten_numbers),
			delta,
			percentDelta: getFormattedValue(percentDelta, decimal, shorten_numbers),
			prefix,
			suffix,
		}
	})
})

const getFormattedValue = (value: number, decimal?: number, shorten_numbers?: boolean) => {
	if (isNaN(value)) return 0
	if (shorten_numbers) {
		return getShortNumber(value, decimal)
	}
	return formatNumber(value, decimal)
}

function getNumberOption(index: number, option: keyof NumberColumnOptions) {
	const numberOption = config.value.number_column_options?.[index]?.[option] as any
	return numberOption === undefined ? config.value[option] : numberOption
}

function onDoubleClick(measure_name: string) {
	const column = props.result.columns.find((c) => c.name === measure_name)
	const row = props.result.formattedRows.at(-1)
	if (column && row) {
		emit('drillDown', column, row)
	}
}
</script>

<template>
	<div class="h-full w-full overflow-hidden p-[2px] @container">
		<div
			class="grid h-full w-full grid-cols-1 gap-4 @xs:grid-cols-2 @sm:grid-cols-2 @md:grid-cols-2 @lg:grid-cols-2 @xl:grid-cols-3 @3xl:grid-cols-4 @4xl:grid-cols-5"
		>
			<div
				v-for="{
					measure_name,
					values,
					currentValue,
					delta,
					percentDelta,
					prefix,
					suffix,
				} in cards"
				:key="measure_name"
				class="flex max-h-[140px] items-center gap-2 overflow-hidden rounded bg-white px-6 pt-5 shadow cursor-pointer"
				:class="config.comparison ? 'pb-6' : 'pb-3'"
				@dblclick="onDoubleClick(measure_name)"
			>
				<div class="flex w-full flex-col">
					<span class="truncate text-sm font-medium">
						{{ measure_name }}
					</span>
					<div class="flex-1 flex-shrink-0 truncate text-[24px] font-semibold leading-10">
						{{ prefix }}{{ currentValue }}{{ suffix }}
					</div>
					<div
						v-if="config.comparison"
						class="flex items-center gap-1 text-xs font-medium"
						:class="[
							config.negative_is_better
								? delta >= 0
									? 'text-red-500'
									: 'text-green-500'
								: delta >= 0
								  ? 'text-green-500'
								  : 'text-red-500',
						]"
					>
						<span class="">
							{{ delta >= 0 ? '↑' : '↓' }}
						</span>
						<span> {{ percentDelta }}% </span>
					</div>
					<div v-if="config.sparkline" class="mt-2 h-[18px] w-[80px]">
						<Sparkline
							:dates="dateValues"
							:values="values"
							:color="config.sparkline_color"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
