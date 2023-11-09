<script setup>
import useDataSource from '@/datasource/useDataSource'
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { computed, defineProps, inject, reactive, ref, watch } from 'vue'

const emit = defineEmits(['save', 'remove', 'discard'])
const props = defineProps({ join: Object })

const builder = inject('builder')
const dataSource = useDataSource(builder.data_source)
!dataSource.tableList.length && dataSource.fetchTables()

const activeJoin = reactive({
	left_table: {},
	left_column: {},
	join_type: {},
	right_table: {},
	right_column: {},
	...props.join,
})

const joinTypeOptions = computed(() => [
	{ label: 'Inner Join', value: 'inner' },
	{ label: 'Left Join', value: 'left' },
])

const leftTableOptions = computed(() => {
	const options = [builder.query.table]
	builder.query.joins.forEach((join) => {
		// exclude the current joined table
		if (join.right_table.table === activeJoin.right_table.table) return
		// exclude the already added tables
		if (options.find((o) => o.table === join.right_table.table)) return
		options.push(join.right_table)
	})
	return options.map((o) => ({ ...o, value: o.table }))
})
const rightTableOptions = computed(() => dataSource?.groupedTableOptions || [])

const leftColumnOptions = ref(null)
const rightColumnOptions = ref(null)
watch(
	() => activeJoin.left_table,
	async (newVal, oldVal) => {
		if (!newVal?.table) return
		if (JSON.stringify(newVal) === JSON.stringify(oldVal)) return
		const leftTable = await useDataSourceTable({
			data_source: builder.data_source,
			table: newVal.table,
		})
		leftColumnOptions.value = leftTable.columns.map((c) => ({
			column: c.column,
			table: c.table,
			label: c.label,
			value: c.column,
		}))
		if (activeJoin.left_column?.table !== newVal.table) {
			activeJoin.left_column = {}
		}
	},
	{ immediate: true, deep: true }
)
watch(
	() => activeJoin.right_table,
	async (newVal, oldVal) => {
		if (!newVal?.table) return
		if (JSON.stringify(newVal) === JSON.stringify(oldVal)) return
		const rightTable = await useDataSourceTable({
			data_source: builder.data_source,
			table: newVal.table,
		})
		rightColumnOptions.value = rightTable.columns.map((c) => ({
			column: c.column,
			table: c.table,
			label: c.label,
			value: c.column,
		}))
		if (activeJoin.right_column?.table !== newVal.table) {
			activeJoin.right_column = {}
		}
	},
	{ immediate: true, deep: true }
)
</script>

<template>
	<div class="flex flex-col gap-1 p-4">
		<span class="text-sm font-medium text-gray-700">Join</span>
		<div class="mb-2 flex gap-2">
			<div class="flex-1">
				<Autocomplete
					v-model="activeJoin.left_table"
					:hideSearch="true"
					:options="leftTableOptions"
					placeholder="Left Table"
				/>
			</div>
			<div class="flex-shrink-0">
				<Autocomplete
					v-model="activeJoin.join_type"
					:hide-search="true"
					:options="joinTypeOptions"
					placeholder="Join Type"
				/>
			</div>
			<div class="flex-1">
				<Autocomplete
					v-model="activeJoin.right_table"
					:options="rightTableOptions"
					placeholder="Right Table"
				/>
			</div>
		</div>
		<span class="text-sm font-medium text-gray-700">Condition</span>
		<div class="mb-2 flex gap-2">
			<div class="flex-1">
				<Autocomplete
					v-model="activeJoin.left_column"
					:options="leftColumnOptions"
					placeholder="Left Column"
				/>
			</div>
			<div class="flex flex-shrink-0 items-center font-mono">=</div>
			<div class="flex-1">
				<Autocomplete
					v-model="activeJoin.right_column"
					:options="rightColumnOptions"
					placeholder="Right Column"
				/>
			</div>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit('discard')">Discard</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" @click="emit('save', activeJoin)">Save</Button>
			</div>
		</div>
	</div>
</template>