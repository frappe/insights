<script setup lang="ts">
import { FileUploader, call } from 'frappe-ui'
import { FileUp } from 'lucide-vue-next'
import { computed, reactive, ref } from 'vue'
import DataTable from '../components/DataTable.vue'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'
import { createToast } from '../helpers/toasts'

const show = defineModel()

const fileUploaded = ref(false)
const csvData = reactive({
	loading: false,
	file: null as File | null,
	tablename: '',
	columns: [] as QueryResultColumn[],
	rows: [] as QueryResultRow[],
	totalRowCount: 0,
})

function uploadFile(file: File) {
	fileUploaded.value = true
	csvData.loading = true
	csvData.file = file
	return call('insights.api.get_file_data', {
		filename: file.name,
	})
		.then((data: any) => {
			csvData.tablename = data.tablename || file.name.split('.')[0] || 'imported_table'
			csvData.columns = data.columns
			csvData.rows = data.rows
			csvData.totalRowCount = data.total_rows
		})
		.catch((error: any) => {
			createToast({
				title: 'Upload Failed',
				message: error?.message || 'Failed to process uploaded file',
				variant: 'error',
			})
			fileUploaded.value = false
			throw error
		})
		.finally(() => {
			csvData.loading = false
		})
}

const importing = ref(false)
const importDisabled = computed(() => {
	return !csvData.file || !csvData.tablename || !csvData.columns.length || importing.value
})
function importCSVData() {
	if (importDisabled.value) return
	if (!csvData.file) return

	importing.value = true
	return call('insights.api.import_csv_data', {
		filename: csvData.file.name,
	})
		.then(() => {
			
				createToast({
					title: 'Table Imported',
					message: `Table '${csvData.tablename}' imported successfully`,
					variant: 'success',
				})
		})
		.catch((error: any) => {
			createToast({
				title: 'Import Failed',
				message: error?.message || 'Failed to import table',
				variant: 'error',
			})
		})
		.finally(() => {
			importing.value = false
			show.value = false
		})
}

function resetFile() {
	fileUploaded.value = false
	csvData.file = null
	csvData.tablename = ''
	csvData.columns = []
	csvData.rows = []
	csvData.totalRowCount = 0
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: csvData.tablename ? 'Import Table' : 'Upload CSV/Excel File',
			size: fileUploaded ? '4xl' : '',
		}"
	>
		<template #body-content>
			<FileUploader
				v-if="!fileUploaded"
				:uploadArgs="{ private: true }"
				:file-types="['.csv', '.xlsx']"
				@success="uploadFile"
			>
				<template #default="{ progress, uploading, openFileSelector }">
					<div
						class="flex cursor-pointer flex-col items-center justify-center gap-3 rounded border border-dashed border-gray-400 p-12 text-base"
						@click="openFileSelector"
					>
						<FileUp
							v-if="!uploading"
							class="h-6 w-6 text-gray-600"
							stroke-width="1.2"
						/>
						<div class="text-center">
							<p v-if="!uploading" class="text-sm font-medium text-gray-800">
								Select a CSV or Excel file to upload
							</p>
							<p v-if="!uploading" class="mt-1 text-xs text-gray-600">
								or drag and drop it here
							</p>
							<div v-else class="flex w-[15rem] flex-col gap-2">
								<div class="h-2 w-full rounded-full bg-gray-200">
									<div
										class="h-2 rounded-full bg-blue-500 transition-all"
										:style="{ width: `${progress}%` }"
									></div>
								</div>
								<p class="text-xs">Uploading...</p>
							</div>
						</div>
					</div>
				</template>
			</FileUploader>

			<div v-else class="flex flex-col gap-4">
				<div>
					<FormControl class="w-fit" label="Table Name" v-model="csvData.tablename" />
				</div>
				<div
					class="relative flex h-[30rem] w-full flex-col overflow-hidden rounded border bg-white"
				>
					<DataTable
						:columns="csvData.columns"
						:rows="csvData.rows"
						:loading="csvData.loading"
					>
						<template #footer-left>
							<p class="tnum p-1 text-sm text-gray-600">
								Showing {{ csvData.rows.length }} of
								{{ csvData.totalRowCount }} rows
							</p>
						</template>
					</DataTable>
				</div>
			</div>
			<div class="mt-4 flex justify-between pt-2">
				<div class="ml-auto flex items-center space-x-2">
					<Button :disabled="!fileUploaded" @click="resetFile"> Reset File </Button>
					<Button
						variant="solid"
						:disabled="importDisabled"
						:loading="importing"
						@click="importCSVData"
					>
						Import
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
