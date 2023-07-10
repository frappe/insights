<script setup>
import { computed, reactive, ref } from 'vue'
import Form from '../pages/Form.vue'
import useDataSources from './useDataSources'

const props = defineProps({ submitLabel: String })
const emit = defineEmits(['submit'])

const database = reactive({})
const form = ref(null)
const fields = computed(() => [
	{ name: 'title', label: 'Title', type: 'text', placeholder: 'My Database', required: true },
	{
		label: 'Host',
		name: 'host',
		type: 'text',
		placeholder: 'localhost',
		required: !database.connection_string,
		defaultValue: 'localhost',
	},
	{
		label: 'Port',
		name: 'port',
		type: 'number',
		placeholder: '3306',
		required: !database.connection_string,
		defaultValue: 3306,
	},
	{
		label: 'Database Name',
		name: 'name',
		type: 'text',
		placeholder: 'DB_1267891',
		required: !database.connection_string,
	},
	{
		label: 'Username',
		name: 'username',
		type: 'text',
		placeholder: 'read_only_user',
		required: !database.connection_string,
	},
	{
		label: 'Password',
		name: 'password',
		type: 'password',
		placeholder: '**********',
		required: !database.connection_string,
	},
	{ label: 'Use secure connection (SSL)?', name: 'useSSL', type: 'checkbox' },
])

const sources = useDataSources()
const areRequiredFieldsFilled = computed(() => {
	return Boolean(
		fields.value.filter((field) => field.required).every((field) => database[field.name]) ||
			(database.title && database.connection_string)
	)
})
const testConnectionDisabled = computed(() => {
	return areRequiredFieldsFilled.value === false || sources.testing
})

const connected = ref(null)
const connectAppearance = computed(() => {
	if (sources.testing || connected.value === null) return 'white'
	if (connected.value) return 'success'
	return 'danger'
})
const connectLabel = computed(() => {
	if (sources.testing) return ''
	if (connected.value === null) return 'Connect'
	if (connected.value) return 'Connected'
	return 'Failed, Retry?'
})
const connectIcon = computed(() => {
	if (connected.value === null) return
	if (connected.value) return 'check'
	return 'alert-circle'
})

const submitDisabled = computed(() => {
	return areRequiredFieldsFilled.value === false || !connected.value || sources.creating
})
const submitLabel = computed(() => {
	if (sources.creating) return ''
	return props.submitLabel || 'Add Database'
})

const testing = ref(false)
const testConnection = async () => {
	database['type'] = 'PostgreSQL'
	testing.value = true
	connected.value = await sources.testConnection({ database })
	testing.value = false
}

const creating = ref(false)
const createNewDatabase = async () => {
	database['type'] = 'PostgreSQL'
	creating.value = true
	await sources.createDatabase({ database })
	creating.value = false
	emit('submit')
}
</script>
<template>
	<Form ref="form" class="flex-1" v-model="database" :meta="{ fields }"> </Form>

	<div class="my-4 flex items-center space-x-2 text-sm">
		<p class="mb-0.5 h-1 flex-1 border-b" />
		<p>OR</p>
		<p class="mb-0.5 h-1 flex-1 border-b" />
	</div>

	<Input
		v-model="database.connection_string"
		label="Connection String"
		placeholder="postgres://user:password@host:port/database"
	/>

	<div class="mt-6 flex justify-between pt-2">
		<div class="ml-auto flex items-center space-x-2">
			<Button
				:appearance="connectAppearance"
				:disabled="testConnectionDisabled"
				@click="testConnection"
				loadingText="Connecting..."
				:loading="testing"
				:iconLeft="connectIcon"
			>
				{{ connectLabel }}
			</Button>
			<Button
				appearance="primary"
				:disabled="submitDisabled"
				loadingText="Adding Database..."
				:loading="creating"
				@click="createNewDatabase"
				class="!rounded-lg bg-gray-900 text-gray-50 hover:bg-gray-800"
			>
				{{ submitLabel }}
			</Button>
		</div>
	</div>
</template>
