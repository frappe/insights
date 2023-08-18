<script setup>
import Form from '@/pages/Form.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { computed, reactive, ref } from 'vue'

const props = defineProps({ submitLabel: String })
const emit = defineEmits(['submit'])

const database = reactive({})
const form = ref(null)
const fields = [
	{ name: 'title', label: 'Title', type: 'text', placeholder: 'My Database', required: true },
	{
		label: 'Host',
		name: 'host',
		type: 'text',
		placeholder: 'localhost',
		required: true,
		defaultValue: 'localhost',
	},
	{
		label: 'Port',
		name: 'port',
		type: 'number',
		placeholder: '3306',
		required: true,
		defaultValue: 3306,
	},
	{
		label: 'Database Name',
		name: 'name',
		type: 'text',
		placeholder: 'DB_1267891',
		required: true,
	},
	{
		label: 'Username',
		name: 'username',
		type: 'text',
		placeholder: 'read_only_user',
		required: true,
	},
	{
		label: 'Password',
		name: 'password',
		type: 'password',
		placeholder: '**********',
		required: true,
	},
	{ label: 'Use secure connection (SSL)?', name: 'useSSL', type: 'checkbox' },
]

const sources = useDataSourceStore()
const areRequiredFieldsFilled = computed(() => {
	return Boolean(fields.filter((field) => field.required).every((field) => database[field.name]))
})
const testConnectionDisabled = computed(() => {
	return areRequiredFieldsFilled.value === false || sources.testing
})

const connected = ref(null)
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
	database['type'] = 'MariaDB'
	testing.value = true
	connected.value = await sources.testConnection({ database })
	testing.value = false
}

const creating = ref(false)
const createNewDatabase = async () => {
	database['type'] = 'MariaDB'
	creating.value = true
	await sources.create({ database })
	creating.value = false
	emit('submit')
}
</script>

<template>
	<Form ref="form" class="flex-1" v-model="database" :meta="{ fields }"> </Form>
	<div class="mt-6 flex justify-between pt-2">
		<div class="ml-auto flex items-center space-x-2">
			<Button
				variant="outline"
				:disabled="testConnectionDisabled"
				@click="testConnection"
				loadingText="Connecting..."
				:loading="testing"
				:iconLeft="connectIcon"
			>
				{{ connectLabel }}
			</Button>
			<Button
				variant="solid"
				:disabled="submitDisabled"
				loadingText="Adding Database..."
				:loading="creating"
				@click="createNewDatabase"
			>
				{{ submitLabel }}
			</Button>
		</div>
	</div>
</template>
