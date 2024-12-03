<script setup lang="ts">
import { computed, ref } from 'vue'
import Form from '../components/Form.vue'
import useDataSourceStore from './data_source'
import { DuckDBDataSource } from './data_source.types'

const show = defineModel({
	default: false,
})

const database = ref<DuckDBDataSource>({
	database_type: 'DuckDB',
	title: '',
	database_name: '',
})

const form = ref()
const fields = [
	{
		name: 'title',
		label: 'Title',
		type: 'text',
		placeholder: 'My Database',
		required: true,
	},
	{
		label: 'File URL',
		name: 'database_name',
		type: 'text',
		placeholder: 'https://example.com/file.duckdb',
		required: true,
		description: 'Enter the URL of the DuckDB file',
	},
]

const isValidFileURL = computed(() => {
	const url = new URL(database.value.database_name)
	return url.protocol === 'https:' || url.protocol === 'http:'
})

const sources = useDataSourceStore()

const connected = ref<boolean | null>(null)
const connectButton = computed(() => {
	const _button = {
		label: 'Connect',
		disabled:
			form.value?.hasRequiredFields === false || !isValidFileURL.value || sources.testing,
		loading: sources.testing,
		variant: 'subtle',
		theme: 'gray',
		onClick() {
			sources.testConnection(database.value).then((result: boolean) => {
				connected.value = Boolean(result)
			})
		},
	}

	if (sources.testing) {
		_button.label = 'Connecting...'
	} else if (connected.value) {
		_button.label = 'Connected'
		_button.variant = 'outline'
		_button.theme = 'green'
	} else if (connected.value === false) {
		_button.label = 'Failed, Retry?'
		_button.variant = 'outline'
		_button.theme = 'red'
	}

	return _button
})

const submitButton = computed(() => {
	return {
		label: 'Add Data Source',
		disabled:
			form.value?.hasRequiredFields === false ||
			!isValidFileURL.value ||
			!connected.value ||
			sources.creating,
		loading: sources.creating,
		variant: connected.value ? 'solid' : 'subtle',
		onClick() {
			sources.createDataSource(database.value).then(() => {
				show.value = false
			})
		},
	}
})
</script>

<template>
	<Dialog v-model="show" :options="{ title: 'Connect to DuckDB' }">
		<template #body-content>
			<Form
				ref="form"
				class="flex-1"
				v-model="database"
				:fields="fields"
				:actions="[connectButton, submitButton]"
			>
			</Form>
		</template>
	</Dialog>
</template>
