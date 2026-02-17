<script setup>
import ChartTitle from '@/components/Charts/ChartTitle.vue'
import TanstackTable from '@/components/Table/TanstackTable.vue'
import { watchDebounced } from '@vueuse/core'
import { computed, ref, watch } from 'vue'
import { convertToNestedObject, convertToTanstackColumns, pivotData } from './utils'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const _data = computed(() => props.data)
watch(_data, reloadPivotData, { deep: true })

const indexColumns = computed(() => props.options.rows?.map((column) => column.value) || [])
const pivotColumns = computed(() => props.options.columns?.map((column) => column.value) || [])
const valueColumns = computed(() => props.options.values?.map((column) => column.value) || [])

const pivotedData = ref([])
watchDebounced(
	[indexColumns, pivotColumns, valueColumns],
	(newVal, oldVal) => {
		if (JSON.stringify(newVal) == JSON.stringify(oldVal)) return
		reloadPivotData()
	},
	{
		deep: true,
		immediate: true,
		debounce: 500,
	}
)

function reloadPivotData() {
	const result = pivotData(_data.value, indexColumns.value, pivotColumns.value, valueColumns.value)
	pivotedData.value = sortIndexKeys(result)
}

function sortIndexKeys(data) {
	// move the index columns (keys) to the front of the object
	return data.map((row) => {
		const indexKeyValues = indexColumns.value.reduce((acc, key) => {
			acc[key] = row[key]
			return acc
		}, {})
		return { ...indexKeyValues, ...row }
	})
}

const tanstackColumns = computed(() => {
	if (!pivotedData.value.length) return []

	const firstPivotedRow = pivotedData.value[0]
	if (!firstPivotedRow) return []

	const nestedRowObject = convertToNestedObject(firstPivotedRow)
	return convertToTanstackColumns(nestedRowObject)
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<ChartTitle :title="props.options.title" />
		<TanstackTable
			v-if="props.options?.columns?.length || props.data?.length"
			:data="pivotedData"
			:columns="tanstackColumns"
			:showFooter="Boolean(props.options.showTotal)"
			:showFilters="Boolean(props.options.filtersEnabled)"
		/>
	</div>
</template>
