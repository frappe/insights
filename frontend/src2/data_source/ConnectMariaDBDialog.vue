<script setup lang="ts">
import { computed, ref } from 'vue'
import Form from '../components/Form.vue'
import useDataSourceStore from './data_source'
import { MariaDBDataSource } from './data_source.types'
import { __ } from '../translation'

const show = defineModel({
	default: false,
})

const database = ref<MariaDBDataSource>({
	database_type: 'MariaDB',
	title: '',
	host: 'localhost',
	port: 3306,
	database_name: '',
	username: '',
	password: '',
	use_ssl: false,
})

const form = ref()
const fields = [
	{
		name: 'title',
		label: __('Title'),
		type: 'text',
		placeholder: __('My Database'),
		required: true,
	},
	{
		label: __('Host'),
		name: 'host',
		type: 'text',
		placeholder: 'localhost',
		required: true,
		defaultValue: 'localhost',
	},
	{
		label: __('Port'),
		name: 'port',
		type: 'number',
		placeholder: '3306',
		required: true,
		defaultValue: 3306,
	},
	{
		label: __('Database Name'),
		name: 'database_name',
		type: 'text',
		placeholder: 'DB_1267891',
		required: true,
	},
	{
		label: __('Username'),
		name: 'username',
		type: 'text',
		placeholder: __('read_only_user'),
		required: true,
	},
	{
		label: __('Password'),
		name: 'password',
		type: 'password',
		placeholder: '**********',
		required: true,
	},
	{ label: __('Use secure connection (SSL)?'), name: 'use_ssl', type: 'checkbox' },
]

const sources = useDataSourceStore()

const connected = ref<boolean | null>(null)
const connectButton = computed(() => {
	const _button = {
		label: __('Connect'),
		disabled: form.value?.hasRequiredFields === false || sources.testing || sources.creating,
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
		label: __('Add Data Source'),
		disabled: form.value?.hasRequiredFields === false || !connected.value || sources.creating,
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
	<Dialog v-model="show" :options="{ title: __('Connect to MariaDB') }">
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
