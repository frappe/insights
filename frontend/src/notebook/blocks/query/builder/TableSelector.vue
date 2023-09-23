<script setup lang="jsx">
import useDataSource from '@/datasource/useDataSource'
import { whenever } from '@vueuse/core'
import { Suspense, computed, ref } from 'vue'
import InputWithPopover from './InputWithPopover.vue'
import TableTooltip from './TableTooltip.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	data_source: String,
	modelValue: Object,
	tableOptions: Array,
})
const table = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
let tables = ref(props.tableOptions || [])
if (!props.tableOptions) {
	let dataSource = useDataSource(props.data_source)
	dataSource.fetchTables()
	whenever(
		() => props.data_source,
		(newVal, oldVal) => {
			if (newVal == oldVal) return
			dataSource = useDataSource(props.data_source)
			dataSource.fetchTables()
		}
	)
	tables = computed(() => dataSource.dropdownOptions)
}
</script>

<template>
	<div>
		<InputWithPopover
			v-model="table"
			:items="tables"
			placeholder="Pick a table"
		></InputWithPopover>
	</div>
</template>
