<script setup>
import { call } from 'frappe-ui'
import { inject, ref } from 'vue'
import FileSourceForm from '../datasource/FileSourceForm.vue'
import MariaDBForm from '../datasource/MariaDBForm.vue'
import PostgreSQLForm from '../datasource/PostgreSQLForm.vue'
import SampleDatasetList from '../datasource/SampleDatasetList.vue'

const emit = defineEmits(['next', 'prev'])
const setupState = inject('setupState')

const sitename = window.location.hostname
const erpnextSiteTitle = ref(sitename)
async function updateERPNextSourceTitle() {
	if (erpnextSiteTitle.value === '') {
		$notify({
			title: 'Please enter a title',
			message: 'Please enter a title to continue',
			type: 'error',
		})
		return
	}

	await call('insights.api.setup.update_erpnext_source_title', {
		title: erpnextSiteTitle.value,
	})
	emit('next')
}
</script>

<template>
	<div class="mt-4 flex flex-col overflow-hidden">
		<div class="flex flex-1 flex-col overflow-y-auto">
			<div v-if="setupState.sourceType == 'erpnext'">
				<Input v-model="erpnextSiteTitle" label="Title" />
				<div class="mt-6 flex flex-shrink-0 justify-end space-x-3">
					<Button variant="solid" @click="updateERPNextSourceTitle"> Continue </Button>
				</div>
			</div>
			<div v-if="setupState.sourceType == 'mariadb'">
				<MariaDBForm @submit="emit('next')" submitLabel="Continue" />
			</div>
			<div v-if="setupState.sourceType == 'postgresql'">
				<PostgreSQLForm @submit="emit('next')" submitLabel="Continue" />
			</div>
			<div v-if="setupState.sourceType == 'file'">
				<FileSourceForm @submit="emit('next')" />
			</div>
			<div v-if="setupState.sourceType == 'sample'">
				<SampleDatasetList @submit="emit('next')" />
			</div>
		</div>
	</div>
</template>
