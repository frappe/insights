<script setup>
import { computed, reactive, ref } from 'vue'
import Form from '../pages/Form.vue'
import useDataSources from './useDataSources'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show'])
const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

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

const sources = useDataSources()
const areRequiredFieldsFilled = computed(() => {
	return fields.filter((field) => field.required).every((field) => database[field.name])
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
	return 'Add Database'
})

const testConnection = async () => {
	database['type'] = 'MariaDB'
	connected.value = await sources.testConnection({ database })
}

const createNewDatabase = async () => {
	database['type'] = 'MariaDB'
	await sources.createDatabase({ database })
	show.value = false
}
</script>
<template>
	<Dialog v-model="show" :options="{ title: 'Connect to MySQL' }">
		<template #body-content>
			<Form ref="form" class="flex-1" v-model="database" :meta="{ fields }"> </Form>
			<div class="mt-6 flex justify-between pt-2">
				<div class="ml-auto flex items-center space-x-2">
					<Button
						:appearance="connectAppearance"
						:disabled="testConnectionDisabled"
						@click="testConnection"
						loadingText="Connecting..."
						:loading="sources.testing"
						:iconLeft="connectIcon"
					>
						{{ connectLabel }}
					</Button>
					<Button
						appearance="primary"
						:disabled="submitDisabled"
						loadingText="Adding Database..."
						:loading="sources.creating"
						@click="createNewDatabase"
					>
						{{ submitLabel }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
