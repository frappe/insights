<template>
	<div class="flex h-full w-1/3 flex-col overflow-scroll pr-4 pb-2">
		<!-- Picker -->
		<div v-if="!editTable" class="flex flex-1 flex-col">
			<div
				v-if="!addingTable"
				class="sticky top-0 flex items-center justify-between bg-white pb-3 pt-1"
			>
				<div class="text-sm tracking-wide text-gray-600">TABLES</div>
				<Button icon="plus" @click="addingTable = true"></Button>
			</div>
			<div v-if="addingTable" class="mb-4 w-full">
				<Autocomplete
					ref="tableSearch"
					v-model="newTable"
					:options="newTableOptions"
					placeholder="Select a table..."
					@selectOption="
						(table) => {
							addingTable = false
							table && query.addTable.submit({ table })
						}
					"
				/>
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
					@click.prevent.stop="editTable = table"
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
		<div v-else>
			<div class="sticky top-0 flex items-center bg-white pb-3 pt-1">
				<Button icon="chevron-left" class="mr-2" @click="editTable = null"> </Button>
				<div class="text-sm tracking-wide text-gray-600">JOIN</div>
			</div>
			<div class="flex flex-col space-y-3">
				<div class="flex flex-col space-y-3">
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">Type</div>
						<Autocomplete
							v-model="join.type"
							:options="joinTypeOptions"
							placeholder="Select a type..."
						/>
					</div>
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">With</div>
						<Autocomplete
							v-model="join.with"
							:options="joinTableOptions"
							placeholder="Select a table..."
							@selectOption="onJoinTableSelect"
						/>
					</div>
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">On</div>
						<Autocomplete
							v-model="join.condition"
							:options="joinConditionOptions"
							placeholder="Select a condition..."
						/>
					</div>
				</div>
				<div class="flex justify-end space-x-2">
					<Button :disabled="!editTable.join" @click="clear_join"> Clear </Button>
					<Button
						appearance="primary"
						:disabled="!join.with || !join.condition || !join.type"
						@click="applyJoin"
					>
						Apply
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import { computed, inject, ref, watch } from 'vue'
import { isEmptyObj, ellipsis } from '@/utils'

const query = inject('query')

const newTable = ref({})
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
const newTableOptions = computed(() => {
	return query.fetchTables.data?.message.map((table) => ({
		...table,
		value: table.table,
	}))
})

const join = ref({ with: {}, condition: {}, type: {} })
const editTable = ref(null) // table that is being edited
watch(editTable, (table) => {
	join.value = { with: {}, condition: {}, type: {} }
	if (table) {
		if (table.join) {
			join.value.condition = table.join.condition
			join.value.with = table.join.with
			join.value.type = table.join.type
		}
		query.fetchJoinOptions.submit({ table })
	}
})
const joinTypeOptions = ref([
	{ label: 'Inner', value: 'inner' },
	{ label: 'Left', value: 'left' },
])
const joinOptions = computed(() => query.fetchJoinOptions.data?.message) // is computed
const joinTableOptions = computed(() => {
	return joinOptions.value?.map(({ label, table }) => {
		return { label, value: table }
	})
})
const joinConditionOptions = computed(() => {
	if (!isEmptyObj(join.value.with) && joinOptions.value) {
		return joinOptions.value
			.filter(({ table }) => {
				return table == join.value.with.value
			})
			.map(({ primary_key, foreign_key }) => ({
				label: `${primary_key} = ${foreign_key}`,
				value: `${primary_key} = ${foreign_key}`,
			}))
	}
	return []
})

function onJoinTableSelect(option) {
	join.value.with = option
	join.value.condition = {}
	if (joinConditionOptions.value.length == 1) {
		join.value.condition = joinConditionOptions.value[0]
	}
}
function applyJoin() {
	editTable.value.join = join.value
	query.updateTable.submit({ table: editTable.value })
	editTable.value = null
}
function clear_join() {
	editTable.value.join = ''
	query.updateTable.submit({ table: editTable.value })
	editTable.value = null
}
const $notify = inject('$notify')
function removeTable(table) {
	const validationError = query.tables.validateRemoveTable(table)
	if (validationError) {
		return $notify(validationError)
	}
	query.removeTable.submit({ table })
}
</script>
