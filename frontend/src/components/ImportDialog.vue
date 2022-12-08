<script setup>
import Attachment from './Controls/Attachment.vue'
import Draggable from 'vuedraggable'
import { reactive, watch, computed, ref } from 'vue'
import { createResource } from 'frappe-ui'

const emit = defineEmits(['close'])
const props = defineProps({ show: Boolean, dataSource: String })
const columnTypes = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']

const table = reactive({
	label: '',
	file: null,
	ifExists: 'Fail',
})
const columns = ref([])
const getColumns = createResource({
	method: 'insights.api.get_columns_from_csv',
	initialData: [],
	onSuccess: (data) => {
		columns.value = data?.map((c) => {
			return {
				column: c,
				type: 'String',
			}
		})
	},
})

function removeColumn(column) {
	columns.value = columns.value.filter((c) => c.column !== column)
}

const importDisabled = computed(() => !table.label || !table.file || columns.length === 0)
watch(
	() => table.file,
	(newFile) => {
		newFile ? getColumns.submit({ file: newFile }) : (getColumns.data = [])
	}
)

const upload = createResource({
	method: 'insights.api.upload_csv',
})

const importingTable = ref(false)
function submit() {
	importingTable.value = true
	const data = {
		data_source: props.dataSource,
		label: table.label,
		file: table.file,
		if_exists: table.ifExists,
		columns: columns.value,
	}
	upload
		.submit(data)
		.then(() => {
			emit('close')
			importingTable.value = false
		})
		.catch((err) => {
			importingTable.value = false
			console.error(err)
		})
}
</script>

<template>
	<Dialog :options="{ title: 'Import Table' }" v-model="props.show" @close="emit('close')">
		<template #body-content>
			<!-- Table Name, Table Label, Action if exists, Attach file, Columns -->
			<div class="mb-4 flex gap-4">
				<div class="flex flex-1 flex-col space-y-3">
					<Input
						label="Table Label"
						type="text"
						placeholder="Table Label"
						v-model="table.label"
					/>
					<Attachment
						label="Attach File"
						:value="table.file"
						@change="(f) => (table.file = f)"
					/>
				</div>
				<div class="flex flex-1 flex-col space-y-3">
					<Input
						type="select"
						label="Action if exists"
						v-model="table.ifExists"
						:options="['Fail', 'Overwrite', 'Append']"
					/>
				</div>
			</div>
			<span v-if="columns?.length" class="mb-2 block text-sm leading-4 text-gray-700">
				Columns to import
			</span>
			<div class="max-h-[15rem] overflow-y-auto">
				<Draggable class="w-full" v-model="columns" group="columns" item-key="column">
					<template #item="{ element: column }">
						<div class="flex h-10 w-full cursor-pointer items-center text-gray-600">
							<span
								class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
							>
								{{ column.column }}
							</span>
							<Input
								class="mr-1 !text-sm"
								type="select"
								:options="columnTypes"
								:value="column.type"
								@change="(type) => (column.type = type)"
							/>
							<Button
								icon="x"
								appearance="minimal"
								@click="removeColumn(column.column)"
							/>
						</div>
					</template>
				</Draggable>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				@click="submit"
				:disabled="importDisabled"
				:loading="importingTable"
			>
				Import
			</Button>
		</template>
	</Dialog>
</template>
