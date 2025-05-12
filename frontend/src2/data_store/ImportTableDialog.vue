<script setup lang="ts">
import { computed, reactive, ref, watch, watchEffect } from 'vue'
import { getDataSourceOptions } from '../data_source/data_source'
import { getRowCount, getTableOptions, getTables } from '../data_source/tables'
import { formatNumber } from '../helpers'
import useDataStore from './data_store'

const show = defineModel({
	default: false,
})

const initalTable = {
	data_source: '',
	table_name: '',
	row_limit: 10_000_000,
	table_row_count: 0,
}
const table = reactive({ ...initalTable })

const tableOptions = computed(() => {
	if (!table.data_source) return []
	return getTableOptions(table.data_source)
})
const dataSourceTableQuery = ref('')
watchEffect(() => {
	if (!table.data_source) return
	getTables(table.data_source, dataSourceTableQuery.value)
})

watch(
	() => table.table_name,
	() => {
		if (!table.table_name) {
			table.table_row_count = 0
			return
		}
		getRowCount(table.data_source, table.table_name).then((count) => {
			table.table_row_count = count
		})
	}
)

function cancelImport() {
	Object.assign(table, initalTable)
	show.value = false
}

const dataStore = useDataStore()
const importDisabled = computed(() => !table.table_name)
function importTable() {
	dataStore.importTable(table.data_source, table.table_name, table.row_limit).then(() => {
		show.value = false
	})
}
</script>

<template>
	<Dialog v-model="show" :options="{ title: 'Import Table', size: 'md' }">
		<template #body-content>
			<div class="flex w-full flex-col gap-2">
				<div class="flex flex-col gap-4">
					<Autocomplete
						label="Data Source"
						placeholder="Select Data Source"
						:modelValue="table.data_source"
						@update:modelValue="table.data_source = $event?.value"
						:options="getDataSourceOptions()"
					/>
					<Autocomplete
						label="Table"
						placeholder="Select Table"
						v-model:query="dataSourceTableQuery"
						:disabled="!table.data_source"
						:modelValue="table.table_name"
						@update:modelValue="table.table_name = $event?.value"
						:options="tableOptions"
					/>
					<div v-if="table.table_name">
						<FormControl
							type="number"
							label="No. of rows to import"
							v-model="table.row_limit"
						/>
						<p class="mt-1 text-xs text-gray-500">
							Selected table has {{ formatNumber(table.table_row_count) }} rows.
						</p>
					</div>
				</div>
				<div class="flex w-full justify-end gap-2 pt-2">
					<Button label="Cancel" variant="outline" @click="cancelImport" />
					<Button
						label="Import"
						variant="solid"
						:disabled="importDisabled"
						:loading="dataStore.importingTable"
						@click="importTable"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
