<template>
	<div class="flex flex-1 flex-shrink-0 flex-col overflow-hidden text-gray-900">
		<template v-if="!selectedTable">
			<div
				v-if="!addingTable"
				class="flex flex-shrink-0 items-center justify-between bg-white pb-2"
			>
				<div class="text-sm tracking-wide text-gray-700">TABLES</div>
				<Button icon="plus" @click="addingTable = true"></Button>
			</div>
			<div v-if="addingTable" class="flex w-full flex-shrink-0 space-x-2 pb-3 pt-1">
				<div class="flex-1">
					<Autocomplete
						ref="tableSearch"
						v-model="newTable"
						:options="query.tables.newTableOptions"
						placeholder="Select a table..."
						@update:modelValue="addNewTable"
					/>
				</div>
				<Button icon="x" @click="addingTable = false"></Button>
			</div>
			<div
				v-if="query.tables.data?.length == 0"
				class="flex flex-1 items-center justify-center rounded border-2 border-dashed border-gray-200 text-sm text-gray-700"
			>
				<p>No tables selected</p>
			</div>

			<div v-else class="flex w-full flex-1 select-none flex-col divide-y overflow-y-scroll">
				<div
					v-for="(table, idx) in query.tables.data"
					:key="idx"
					class="flex h-10 w-full cursor-pointer items-center border-b text-sm last:border-0 hover:bg-gray-50"
					@click.prevent.stop="selectedTable = table"
				>
					<FeatherIcon name="layout" class="mr-2 h-[14px] w-[14px]" />
					<span
						class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
					>
						{{ table.label }}
					</span>
					<span v-if="table.join" class="ml-2 text-gray-700">
						<JoinLeftIcon v-if="table.join.type.value == 'left'" />
						<JoinRightIcon v-if="table.join.type.value == 'right'" />
						<JoinInnerIcon v-if="table.join.type.value == 'inner'" />
						<JoinFullIcon v-if="table.join.type.value == 'full'" />
					</span>
					<span
						v-if="table.join"
						class="ml-2 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
					>
						{{ table.join.with.label }}
					</span>
					<span
						class="ml-auto mr-1 overflow-hidden text-ellipsis whitespace-nowrap text-gray-700"
					>
						{{ query.doc.data_source }}
					</span>
					<div
						class="flex items-center px-1 py-0.5 text-gray-700 hover:text-gray-700"
						@click.prevent.stop="removeTable(table)"
					>
						<FeatherIcon name="x" class="h-3 w-3" />
					</div>
				</div>
			</div>
		</template>
		<!-- Editor -->
		<TableJoiner v-else :table="selectedTable" @close="selectedTable = null"></TableJoiner>
	</div>
</template>

<script setup>
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import TableJoiner from './TableJoiner.vue'
import { inject, ref, watch } from 'vue'

const query = inject('query')

const newTable = ref({})
const selectedTable = ref(null)
const addingTable = ref(false)
const tableSearch = ref(null)
watch(addingTable, (newValue) => {
	newTable.value = {}
	if (newValue) {
		query.fetchTables.submit().then(() => {
			tableSearch.value.input.el.focus()
		})
	}
})

const $notify = inject('$notify')

function addNewTable(table) {
	addingTable.value = false
	if (table?.value) {
		query.addTable.submit({
			table: {
				table: table.value,
				label: table.label,
			},
		})
	}
}
function removeTable(table) {
	const validationError = query.tables.validateRemoveTable(table)
	if (validationError) {
		return $notify(validationError)
	}
	query.removeTable.submit({ table })
}
</script>
