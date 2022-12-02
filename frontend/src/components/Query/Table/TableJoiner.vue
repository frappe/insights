<template>
	<div>
		<div class="sticky top-0 flex items-center bg-white pb-3 pt-1">
			<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
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
						:options="query.tables.joinOptions"
						placeholder="Select a table..."
					/>
				</div>
				<div class="space-y-1 text-sm text-gray-600">
					<div class="font-light">On</div>
					<div class="flex items-center space-x-1">
						<div class="flex-1">
							<Autocomplete
								v-model="join.condition.left"
								:options="leftColumnOptions"
								placeholder="Select a Column"
							/>
						</div>
						<span class="px-1 text-lg"> = </span>
						<div class="flex-1">
							<Autocomplete
								v-model="join.condition.right"
								:options="rightColumnOptions"
								placeholder="Select a Column"
							/>
						</div>
					</div>
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
</template>

<script setup>
import { ref, inject, watch } from 'vue'

const emits = defineEmits(['close'])
const props = defineProps({
	table: {
		type: Object,
		required: true,
	},
})

const query = inject('query')
const join = ref({ with: {}, condition: {}, type: {} })
const editTable = ref({ ...props.table }) // table that is being edited

if (editTable.value.join) {
	join.value = editTable.value.join
}

const joinTypeOptions = ref([
	{ label: 'Inner', value: 'inner' },
	{ label: 'Left', value: 'left' },
])

watch(
	() => join.value.with,
	(newVal) => newVal && setJoinCondition()
)

const leftColumnOptions = ref([])
const rightColumnOptions = ref([])
function setJoinCondition() {
	const leftTable = editTable.value.table
	const rightTable = join.value.with.value

	if (!leftTable || !rightTable) return

	query.fetchJoinOptions
		.submit({
			left_table: leftTable,
			right_table: rightTable,
		})
		.then(({ message }) => {
			setJoinConditionOptions(message)
			if (message.saved_links.length) {
				setSavedJoinCondition(message.saved_links[0])
			}
		})
}
function setJoinConditionOptions({ left_columns, right_columns }) {
	leftColumnOptions.value = left_columns.map((c) => ({
		label: c.label,
		value: c.column,
	}))
	rightColumnOptions.value = right_columns.map((c) => ({
		label: c.label,
		value: c.column,
	}))
}
function setSavedJoinCondition({ left, right }) {
	join.value.condition = {
		left: leftColumnOptions.value.find((col) => col.value === left),
		right: rightColumnOptions.value.find((col) => col.value === right),
	}
}
function applyJoin() {
	editTable.value.join = join.value
	query.updateTable.submit({ table: editTable.value })
	emits('close')
}
function clear_join() {
	editTable.value.join = ''
	query.updateTable.submit({ table: editTable.value })
	emits('close')
}
</script>
