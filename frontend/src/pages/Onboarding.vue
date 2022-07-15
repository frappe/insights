<template>
	<div class="flex flex-col items-center py-24">
		<header class="flex h-20 items-center justify-center py-4">
			<h1 class="text-3xl font-bold leading-tight text-gray-900">Setup</h1>
		</header>
		<main
			class="flex h-[calc(100%-5rem)] w-[38rem] flex-col space-y-6 rounded-md border bg-white p-8 py-6 text-base shadow-md"
		>
			<div class="text-lg font-semibold text-gray-800">Add Database</div>
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
						label="Host"
						placeholder="localhost"
						autocomplete="off"
					/>
					<Input
						v-model="db.port"
						type="number"
						label="Port"
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
			<div class="flex justify-end space-x-2">
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
		</main>
	</div>
</template>

<script setup>
import { computed, nextTick, reactive } from 'vue'
import { createDatabase, testDatabaseConnection } from '@/controllers/onboarding'
import { useRouter } from 'vue-router'

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
