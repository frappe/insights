<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { getDataSourceOptions } from '../data_source/data_source'
import { getTableOptions, getTables } from '../data_source/tables'
import { formatNumber } from '../helpers'
import useDataStore from './data_store'
import { useTableSelection } from './table_selection'
import { __ } from '../translation'

const show = defineModel({
	default: false,
})

const ROW_LIMIT = 10_000_000
const table = useTableSelection()
const rowLimit = ref(ROW_LIMIT)

const tableOptions = computed(() => {
	if (!table.data_source) return []
	return getTableOptions(table.data_source)
})
const dataSourceTableQuery = ref('')
watchEffect(() => {
	if (!table.data_source) return
	getTables(table.data_source, dataSourceTableQuery.value)
})

function cancelImport() {
	table.reset()
	rowLimit.value = ROW_LIMIT
	show.value = false
}

const dataStore = useDataStore()
const importDisabled = computed(() => !table.table_name)
function importTable() {
	dataStore.importTable(table.data_source, table.table_name, rowLimit.value).then(() => {
		show.value = false
	})
}
</script>

<template>
	<Dialog v-model:open="show" :title="__('Import Table')" size="md">
		<template #default>
			<div class="flex w-full flex-col gap-2">
				<div class="flex flex-col gap-4">
					<Combobox
						label="Data Source"
						placeholder="Select Data Source"
						:modelValue="table.data_source"
						@update:modelValue="table.pickSource($event)"
						:options="getDataSourceOptions()"
					/>
					<Combobox
						label="Table"
						placeholder="Select Table"
						@update:query="dataSourceTableQuery = $event"
						:disabled="!table.data_source"
						:modelValue="table.table_name"
						@update:modelValue="table.pickTable($event)"
						:options="tableOptions"
					/>
					<div v-if="table.table_name">
						<FormControl
							type="number"
							label="No. of rows to import"
							v-model="rowLimit"
						/>
						<p class="mt-1 text-xs text-ink-gray-4">
							<template v-if="table.table_row_count !== undefined">
								{{
									__(
										'Selected table has {0} rows.',
										formatNumber(table.table_row_count),
									)
								}}
							</template>
							<template v-else>
								{{ __('The number of rows in this table is not available.') }}
							</template>
						</p>
					</div>
				</div>
				<div class="flex w-full justify-end gap-2 pt-2">
					<Button label="Cancel" variant="outline" @click="cancelImport" />
					<Button
						:label="__('Import')"
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
