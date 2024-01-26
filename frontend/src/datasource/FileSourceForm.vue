<script setup>
import Attachment from '@/components/Controls/Attachment.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { FileUploader, createResource } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import Draggable from 'vuedraggable'

const emit = defineEmits(['submit'])

const columnTypes = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']
const table = reactive({
	label: '',
	name: '',
	data_source: 'Query Store',
	file: null,
	ifExists: 'Overwrite',
})
const columns = ref([])
const getColumns = createResource({
	url: 'insights.api.data_sources.get_columns_from_uploaded_file',
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

const importDisabled = computed(
	() =>
		!table.data_source ||
		!table.label ||
		!table.file ||
		columns.length === 0 ||
		importingTable.value
)
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
	url: 'insights.api.data_sources.import_csv',
})

const dataSourceStore = useDataSourceStore()
const importingTable = ref(false)
function submit() {
	importingTable.value = true
	const data = {
		table_label: table.label,
		table_name: table.name,
		filename: table.file.name,
		if_exists: table.ifExists,
		columns: columns.value,
		data_source: table.data_source,
	}
	import_csv
		.submit(data)
		.then(() => {
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
	table.data_source = ''
	columns.value = []
	importingTable.value = false
}
</script>

<template>
	<div>
		<FileUploader v-if="false" @success="(file) => (table.file = file)">
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
						<p v-if="!uploading" class="mt-1 text-center text-xs">
							Only CSV files upto 10MB
						</p>
					</div>
				</div>
			</template>
		</FileUploader>
		<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
			<transition-group name="fade">
				<div>
					<span class="mb-2 block text-sm leading-4 text-gray-700">Data Source</span>
					<Autocomplete
						v-model="table.data_source"
						:returnValue="true"
						:options="dataSourceStore.getDropdownOptions({ allow_imports: 1 })"
						placeholder="Select Data Source"
					/>
				</div>
				<Attachment
					v-model="table.file"
					label="File"
					fileType=".csv"
					placeholder="Upload CSV File"
				/>
				<Input
					v-if="table.file"
					label="New Table Label"
					type="text"
					placeholder="eg. Sales Data"
					v-model="table.label"
				/>
				<Input
					v-if="table.file"
					label="New Table Name"
					type="text"
					placeholder="eg. sales_data"
					v-model="table.name"
				/>
				<Input
					v-if="table.file"
					type="select"
					label="Action if exists"
					v-model="table.ifExists"
					:options="['Fail', 'Overwrite', 'Append']"
				/>
			</transition-group>
		</div>
	</div>
	<div v-if="table.data_source && table.file" class="mt-4">
		<span class="text-base font-medium leading-6 text-gray-900"> Columns </span>
		<div
			v-if="columns?.length"
			class="mt-2 flex max-h-[15rem] flex-col overflow-hidden text-base"
		>
			<div
				class="sticky right-0 top-0 z-10 flex h-8 w-full cursor-pointer items-center space-x-8 pr-8 pb-1 text-xs uppercase text-gray-600"
			>
				<span class="flex-1"> CSV Column </span>
				<span class="flex-1"> Column Name </span>
				<span class="flex-1"> Column Type </span>
			</div>
			<div class="flex flex-col overflow-y-auto">
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
		<div
			v-else-if="getColumns.loading"
			class="mt-2 flex flex-col items-center justify-center space-y-2 p-12 text-center text-sm"
		>
			<LoadingIndicator class="h-4 w-4 text-gray-500" />
			<p class="text-gray-600">Loading columns...</p>
		</div>
		<div v-else class="mt-2 flex flex-col space-y-3 p-12 text-center text-sm text-gray-600">
			No columns found in the uploaded file.<br />
			Please upload a different file.
		</div>
	</div>
	<div class="mt-4 flex justify-between pt-2">
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
