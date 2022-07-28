<template>
	<div class="flex space-x-4">
		<div class="flex-1 space-y-4">
			<Input
				v-model="db.type"
				type="select"
				label="Database Type"
				:options="['MariaDB']"
				autocomplete="off"
			/>
			<Input
				v-model="db.title"
				type="text"
				label="Title"
				placeholder="LocalDB"
				autocomplete="off"
			/>
			<Input
				v-model="db.host"
				type="text"
				label="Host (Optional)"
				placeholder="localhost"
				autocomplete="off"
			/>
			<Input
				v-model="db.port"
				type="number"
				label="Port (Optional)"
				placeholder="1234"
				autocomplete="off"
			/>
			<Input
				v-model="db.useSSL"
				type="checkbox"
				label="Use secure connection (SSL)?"
				autocomplete="off"
			/>
		</div>
		<div class="flex-1 space-y-4">
			<Input
				v-model="db.name"
				type="text"
				label="Database Name"
				placeholder="DB_1267891"
				autocomplete="off"
			/>
			<Input
				v-model="db.username"
				type="text"
				label="Username"
				placeholder="read_only_user"
				autocomplete="off"
			/>
			<Input
				v-model="db.password"
				type="password"
				label="Password"
				placeholder="****"
				autocomplete="off"
			/>
		</div>
	</div>
	<div class="mt-6 flex justify-between">
		<Button @click="$emit('close')"> Prev </Button>
		<div class="space-x-2">
			<Button
				:appearance="connectAppearance"
				:disabled="testConnectionDisabled"
				@click="testConnection"
				loadingText="Connecting..."
				:loading="testDatabaseConnection.loading"
				:iconLeft="connectIcon"
			>
				{{ connectLabel }}
			</Button>
			<Button
				appearance="primary"
				:disabled="submitDisabled"
				loadingText="Adding Database..."
				:loading="createDatabase.loading"
				@click="createNewDatabase"
			>
				{{ submitLabel }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, reactive } from 'vue'
import { createDatabase, testDatabaseConnection } from '@/utils/onboarding'
import { useRouter } from 'vue-router'

defineEmits(['close'])

const db = reactive({
	type: 'MariaDB',
	title: '',
	host: '',
	port: '',
	name: '',
	username: '',
	password: '',
	useSSL: false,
	connectionSuccess: null,
})
const testConnectionDisabled = computed(() => {
	return !db.type || !db.title || !db.name || !db.username || !db.password
})
const submitDisabled = computed(() => {
	return (
		!db.type || !db.title || !db.name || !db.username || !db.password || !db.connectionSuccess
	)
})

const connectAppearance = computed(() => {
	if (testDatabaseConnection.loading || db.connectionSuccess === null) return 'white'
	if (db.connectionSuccess) return 'success'
	return 'danger'
})
const connectLabel = computed(() => {
	if (testDatabaseConnection.loading) return ''
	if (db.connectionSuccess === null) return 'Connect'
	if (db.connectionSuccess) return 'Connected'
	return 'Failed, Retry?'
})
const connectIcon = computed(() => {
	if (db.connectionSuccess === null) return
	if (db.connectionSuccess) return 'check'
	return 'alert-circle'
})

const submitLabel = computed(() => {
	if (createDatabase.loading) return ''
	return 'Add Database'
})

const testConnection = () => {
	testDatabaseConnection.submit({ db }, { onSuccess: (res) => (db.connectionSuccess = res) })
}
const router = useRouter()
const createNewDatabase = () => {
	createDatabase.submit({ db }, { onSuccess: () => nextTick(() => router.push('/')) })
}
</script>
