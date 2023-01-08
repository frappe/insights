<template>
	<div
		class="flex min-h-[20rem] flex-1 flex-col overflow-scroll scrollbar-hide lg:w-1/3 lg:pb-2 lg:pr-4"
	>
		<!-- Picker -->
		<div v-if="!selectedTable" class="flex flex-1 flex-col">
			<div
				v-if="!addingTable"
				class="sticky top-0 flex items-center justify-between bg-white pb-3 pt-1"
			>
				<div class="text-sm tracking-wide text-gray-600">TABLES</div>
				<Button icon="plus" @click="addingTable = true"></Button>
			</div>
			<div v-if="addingTable" class="flex w-full space-x-2 pt-1 pb-3">
				<div class="flex-1">
					<Autocomplete
						ref="tableSearch"
						v-model="newTable"
						:options="query.tables.newTableOptions"
						placeholder="Select a table..."
						@selectOption="addNewTable"
					/>
				</div>
				<Button icon="x" @click="addingTable = false"></Button>
			</div>
			<div
				v-if="query.tables.data?.length == 0"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>No tables selected</p>
			</div>

			<div v-else class="flex w-full flex-1 select-none flex-col divide-y">
				<div
					v-for="(table, idx) in query.tables.data"
					:key="idx"
					class="flex h-10 w-full cursor-pointer items-center border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
					@click.prevent.stop="selectedTable = table"
				>
					<FeatherIcon name="layout" class="mr-2 h-[14px] w-[14px] text-gray-500" />
					<span
						class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
					>
						{{ table.label }}
					</span>
					<span v-if="table.join" class="ml-2 text-gray-500">
						<JoinLeftIcon v-if="table.join.type.value == 'left'" />
						<JoinRightIcon v-if="table.join.type.value == 'right'" />
						<JoinInnerIcon v-if="table.join.type.value == 'inner'" />
						<JoinFullIcon v-if="table.join.type.value == 'full_outer'" />
					</span>
					<span
						v-if="table.join"
						class="ml-2 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
					>
						{{ table.join.with.label }}
					</span>
					<span
						class="ml-auto mr-1 overflow-hidden text-ellipsis whitespace-nowrap font-light text-gray-500"
					>
						{{ query.doc.data_source }}
					</span>
					<div
						class="flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
						@click.prevent.stop="removeTable(table)"
					>
						<FeatherIcon name="x" class="h-3 w-3" />
					</div>
				</div>
			</div>
		</div>
		<!-- Editor -->
		<TableJoiner v-else :table="selectedTable" @close="selectedTable = null"></TableJoiner>
	</div>
</template>

<script setup>
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
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
