<script setup>
import { FileUploader } from 'frappe-ui'
import { computed, ref } from 'vue'
import useDataSources from './useDataSources'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show'])
const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})
const url = ref('')
const createNew = ref(false)
const newDatabaseName = ref('')
const sources = useDataSources()

async function submitCreateNew() {
	if (newDatabaseName.value) {
		const database = { type: 'SQLite', title: newDatabaseName.value }
		await sources.createDatabase({ database })
		show.value = false
	}
}
</script>

<template>
	<Dialog
		:options="{ title: createNew ? 'Create SQLite Database' : 'Connect SQLite Database' }"
		v-model="show"
	>
		<template #body-content>
			<div class="space-y-4 pt-2">
				<FileUploader
					v-if="!createNew"
					file-types=".db"
					@success="(file) => (url = file.file_url)"
				>
					<template v-slot="{ file, progress, uploading, openFileSelector }">
						<div
							class="group flex cursor-pointer items-center space-x-4"
							@click="openFileSelector"
						>
							<div
								class="rounded-md border p-4 text-gray-400 shadow-sm transition-all group-hover:scale-105"
							>
								<FeatherIcon name="upload" class="h-6 w-6 text-gray-400" />
							</div>
							<div>
								<p
									class="text-lg font-medium leading-6 text-gray-900 transition-colors group-hover:text-blue-500"
								>
									Upload Database
								</p>
								<p class="text-sm leading-5 text-gray-500">
									{{
										!uploading && !url
											? 'Upload a .db file up to 10MB'
											: uploading && !url
											? 'Uploading ' + progress + '%'
											: url
									}}
								</p>
							</div>
						</div>
					</template>
				</FileUploader>

				<div
					v-if="!createNew"
					class="group flex cursor-pointer items-center space-x-4"
					@click="createNew = true"
				>
					<div
						class="rounded-md border p-4 text-gray-400 shadow-sm transition-all group-hover:scale-105"
					>
						<FeatherIcon name="plus" class="h-6 w-6 text-gray-400" />
					</div>
					<div>
						<p
							class="text-lg font-medium leading-6 text-gray-900 transition-colors group-hover:text-blue-500"
						>
							Create New
						</p>
						<p class="text-sm leading-5 text-gray-500">Create a new database</p>
					</div>
				</div>

				<div v-if="createNew" class="space-y-4">
					<Input
						v-model="newDatabaseName"
						label="Data Source Name"
						placeholder="eg. My Database"
					/>
					<div class="flex justify-end">
						<Button
							appearance="primary"
							:disabled="!newDatabaseName"
							:loading="loading"
							@click="submitCreateNew"
						>
							Create
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
