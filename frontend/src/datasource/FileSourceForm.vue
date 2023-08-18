<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import { FileUploader, createResource } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import Draggable from 'vuedraggable'

const emit = defineEmits(['submit'])

const columnTypes = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']
const table = reactive({
	label: '',
	name: '',
	file: null,
	ifExists: 'Overwrite',
})
const columns = ref([])
const getColumns = createResource({
	url: 'insights.api.get_columns_from_uploaded_file',
	initialData: [],
	onSuccess: (data) => {
		columns.value = data?.map((c) => {
			return {
				label: c.label,
				name: scrubName(c.label),
				type: c.type || 'String',
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
		table.label = newFile ? newFile.file_name?.replace(/\.[^/.]+$/, '') : ''
		table.name = newFile ? scrubName(table.label) : ''
		newFile ? getColumns.submit({ filename: newFile.name }) : (getColumns.data = [])
	}
)
function scrubName(name) {
	return name?.toLocaleLowerCase().replace(/[^a-zA-Z0-9]/g, '_')
}
const import_csv = createResource({
	url: 'insights.api.import_csv',
})

const importingTable = ref(false)
function submit() {
	importingTable.value = true
	const data = {
		table_label: table.label,
		table_name: table.name,
		filename: table.file.name,
		if_exists: table.ifExists,
		columns: columns.value,
	}
	import_csv
		.submit(data)
		.then(() => {
			useDataSources().reload()
			emit('submit')
			reset()
		})
		.catch((err) => {
			importingTable.value = false
			console.error(err)
		})
}

function reset() {
	table.label = ''
	table.name = ''
	table.file = null
	table.ifExists = 'Overwrite'
	columns.value = []
	importingTable.value = false
}
</script>

<template>
	<div v-if="!table.file">
		<FileUploader @success="(file) => (table.file = file)">
			<template #default="{ progress, uploading, openFileSelector }">
				<div
					class="flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-gray-300 p-8 text-base"
					@click="openFileSelector"
				>
					<FeatherIcon name="upload" class="h-8 w-8 text-gray-500" />
					<div class="mt-2 text-gray-600">
						<p v-if="!uploading" class="text-center font-medium text-blue-500">
							Select a file
						</p>
						<p v-else class="text-center font-medium text-blue-500">
							Uploading... ({{ progress }}%)
						</p>
						<p v-if="!uploading" class="text-center text-xs">
							Only CSV files upto 10MB
						</p>
					</div>
				</div>
			</template>
		</FileUploader>
	</div>
	<div v-else class="mb-4 flex gap-4">
		<div class="flex flex-1 flex-col space-y-3">
			<Input
				label="New Table Label"
				type="text"
				placeholder="eg. Sales Data"
				v-model="table.label"
			/>
			<Input
				label="New Table Name"
				type="text"
				placeholder="eg. sales_data"
				v-model="table.name"
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
	<span v-if="columns?.length" class="text-lg font-medium leading-6 text-gray-900">
		Columns Mapping
	</span>
	<div v-if="columns?.length" class="mt-2 flex max-h-[15rem] flex-col overflow-hidden text-base">
		<div
			class="sticky right-0 top-0 z-10 flex h-8 w-full cursor-pointer items-center space-x-8 pr-8 text-xs uppercase text-gray-600"
		>
			<span class="flex-1"> CSV Column </span>
			<span class="flex-1"> Column Name </span>
			<span class="flex-1"> Column Type </span>
		</div>
		<div class="flex flex-col overflow-y-scroll">
			<Draggable class="w-full" v-model="columns" group="columns" item-key="column">
				<template #item="{ element: column }">
					<div
						class="flex h-10 w-full cursor-pointer items-center space-x-8 text-gray-600"
					>
						<span
							class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
						>
							{{ column.label }}
						</span>
						<Input
							class="flex-1 !text-sm"
							type="text"
							:value="column.name"
							@change="(name) => (column.name = name)"
						/>
						<Input
							class="flex-1 !text-sm"
							type="select"
							:options="columnTypes"
							:value="column.type"
							@change="(type) => (column.type = type)"
						/>
						<Button
							class="!ml-0"
							icon="x"
							variant="minimal"
							@click="removeColumn(column.column)"
						/>
					</div>
				</template>
			</Draggable>
		</div>
	</div>
	<div class="mt-6 flex justify-between pt-2" v-if="table.file">
		<div class="ml-auto flex items-center space-x-2">
			<Button
				variant="solid"
				@click="submit"
				:disabled="importDisabled"
				:loading="importingTable"
			>
				Import
			</Button>
		</div>
	</div>
</template>
