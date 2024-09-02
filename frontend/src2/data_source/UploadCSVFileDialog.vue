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

function uploadFileAndFetchData(file: File) {
	fileUploaded.value = true
	csvData.loading = true
	csvData.file = file
	return call('insights.api.get_csv_data', {
		filename: file.name,
	})
		.then((data: any) => {
			csvData.tablename = data.tablename
			csvData.columns = data.columns
			csvData.rows = data.rows
			csvData.totalRowCount = data.total_rows
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
			show.value = false
			createToast({
				title: 'Table Imported',
				message: `Table '${csvData.tablename}' imported successfully`,
				variant: 'success',
			})
		})
		.finally(() => {
			importing.value = false
		})
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: csvData.tablename ? `Import '${csvData.tablename}' Table` : 'Upload CSV File',
			size: fileUploaded ? '4xl' : '',
		}"
	>
		<template #body-content>
			<FileUploader
				v-if="!fileUploaded"
				:file-types="['.csv']"
				@success="uploadFileAndFetchData"
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
								Select a CSV file to upload
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

			<div
				v-else
				class="relative flex h-[30rem] w-full flex-1 flex-col overflow-hidden rounded border bg-white"
			>
				<div
					v-if="csvData.loading"
					class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
				>
					<LoadingIndicator class="h-8 w-8 text-gray-700" />
				</div>

				<DataTable v-else :columns="csvData.columns" :rows="csvData.rows">
					<template #footer>
						<div class="flex flex-shrink-0 items-center gap-3 border-t p-2">
							<p class="tnum text-sm text-gray-600">
								Showing {{ csvData.rows.length }} of
								{{ csvData.totalRowCount }} rows
							</p>
						</div>
					</template>
				</DataTable>
			</div>
			<div class="mt-4 flex justify-between pt-2">
				<div class="ml-auto flex items-center space-x-2">
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
