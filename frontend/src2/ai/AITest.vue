<script setup lang="ts">
import {
	Badge,
	Button,
	Dropdown,
	FeatherIcon,
	FormControl,
	LoadingIndicator,
	TextInput,
} from 'frappe-ui'
import { Autocomplete } from 'frappe-ui'
import { nextTick, provide, ref, computed } from 'vue'
import { getDataSourceOptions } from '../data_source/data_source'
import { getUniqueId } from '../helpers'
import QueryBuilderToolbar from '../query/components/QueryBuilderToolbar.vue'
import QueryDataTable from '../query/components/QueryDataTable.vue'
import QueryOperations from '../query/components/QueryOperations.vue'
import useQuery from '../query/query'
import {
	createAISession,
	askFollowUp,
	getAISession,
	listAISessions,
	deleteAISession,
} from '../api/ai'
import type { Operation } from '../types/query.types'
import { createToast } from '../helpers/toasts'

type Message = {
	role: 'user' | 'assistant'
	content: string
	operations?: Operation[]
	error?: string
	timestamp?: Date
}

type SessionOption = {
	label: string
	value: string
	description?: string
	question?: string
	dataSource?: string
}

const selectedDataSource = ref('log.frappe.cloud')
const sessionOptions = ref<SessionOption[]>([])
const selectedSession = ref<SessionOption | null>(null)
const currentSessionId = ref<string | null>(null)
const messages = ref<Message[]>([])
const currentQuestion = ref('')
const followUpQuestion = ref('')
const generating = ref(false)
const isQueryReady = ref(false)
const error = ref('')
const loadingSessions = ref(false)

const query = useQuery('new-query-' + getUniqueId())
query.doc.title = 'AI Query'
query.doc.use_live_connection = true
query.autoExecute = true

provide('query', query)

const hasActiveSession = computed(() => currentSessionId.value !== null)
const canSendFollowUp = computed(
	() => hasActiveSession.value && Boolean(followUpQuestion.value.trim()),
)
const canStartSession = computed(
	() =>
		!hasActiveSession.value &&
		Boolean(currentQuestion.value.trim()) &&
		Boolean(selectedDataSource.value),
)
const canSubmitChat = computed(() =>
	hasActiveSession.value ? canSendFollowUp.value : canStartSession.value,
)
const hasMessages = computed(() => messages.value.length > 0)

function submitChat() {
	if (hasActiveSession.value) {
		sendFollowUp()
		return
	}
	createSession()
}

async function loadSessions() {
	loadingSessions.value = true
	try {
		const sessions = await listAISessions()
		sessionOptions.value = sessions.map((s: any) => ({
			label: s.question,
			value: s.session_id,
			description: `${s.data_source} · ${s.message_count} messages`,
			question: s.question,
			dataSource: s.data_source,
		}))
	} catch (e) {
		console.error('Failed to load sessions:', e)
	} finally {
		loadingSessions.value = false
	}
}

async function onSessionSelect(session: SessionOption | string | null) {
	if (!session) return
	const resolvedSession =
		typeof session === 'string'
			? sessionOptions.value.find((option) => option.value === session) || null
			: session
	if (!resolvedSession) return
	selectedSession.value = resolvedSession
	await loadSession(resolvedSession.value)
}

async function createSession() {
	if (!currentQuestion.value.trim()) {
		error.value = 'Please enter a question'
		return
	}
	if (!selectedDataSource.value) {
		error.value = 'Please select a data source'
		return
	}

	generating.value = true
	error.value = ''
	isQueryReady.value = false

	try {
		messages.value = [
			{
				role: 'user',
				content: currentQuestion.value,
				timestamp: new Date(),
			},
		]

		const result = await createAISession(currentQuestion.value, selectedDataSource.value)
		currentSessionId.value = result.session_id
		selectedSession.value = {
			label: currentQuestion.value,
			value: result.session_id,
			question: currentQuestion.value,
			dataSource: selectedDataSource.value,
		}

		messages.value.push({
			role: 'assistant',
			content: result.error
				? `Generated query (with error): ${result.error}`
				: `Generated ${result.operations?.length || 0} operations`,
			operations: result.operations,
			error: result.error,
			timestamp: new Date(),
		})

		createToast({
			title: 'Query Generated',
			message: `Attempt ${result.attempts}/${3}`,
			variant: result.error ? 'warning' : 'success',
		})

		if (result.operations?.length) {
			await nextTick()
			await applyOperations(result.operations)
		}

		await loadSessions()
	} catch (err: any) {
		error.value = err.message || 'Failed to generate query'
		createToast({
			title: 'Error',
			message: error.value,
			variant: 'error',
		})
	} finally {
		generating.value = false
	}
}

async function sendFollowUp() {
	if (!canSendFollowUp.value || !currentSessionId.value) return

	generating.value = true
	error.value = ''

	try {
		messages.value.push({
			role: 'user',
			content: followUpQuestion.value,
			timestamp: new Date(),
		})

		const result = await askFollowUp(currentSessionId.value, followUpQuestion.value)
		followUpQuestion.value = ''

		messages.value.push({
			role: 'assistant',
			content: result.error
				? `Updated query (with error): ${result.error}`
				: result.is_modification
				  ? `Modified query to ${result.operations?.length || 0} operations`
				  : `Generated ${result.operations?.length || 0} operations`,
			operations: result.operations,
			error: result.error,
			timestamp: new Date(),
		})

		createToast({
			title: 'Query Updated',
			message: `Attempt ${result.attempts}/${3}`,
			variant: result.error ? 'warning' : 'success',
		})

		if (result.operations?.length) {
			await nextTick()
			await applyOperations(result.operations)
		}
	} catch (err: any) {
		error.value = err.message || 'Failed to update query'
		createToast({
			title: 'Error',
			message: error.value,
			variant: 'error',
		})
	} finally {
		generating.value = false
	}
}

async function loadSession(sessionId: string) {
	try {
		const session = await getAISession(sessionId)
		currentSessionId.value = session.session_id
		messages.value = session.messages.map((m: any) => ({
			...m,
			timestamp: new Date(),
		}))

		if (session.operations?.length) {
			await nextTick()
			await applyOperations(session.operations)
		}
	} catch (err: any) {
		createToast({
			title: 'Error',
			message: err.message || 'Failed to load session',
			variant: 'error',
		})
	}
}

async function applyOperations(operations: Operation[]) {
	query.setOperations(operations)
	isQueryReady.value = true
}

function newConversation() {
	selectedSession.value = null
	currentSessionId.value = null
	messages.value = []
	currentQuestion.value = ''
	followUpQuestion.value = ''
	error.value = ''
	query.setOperations([])
	isQueryReady.value = false
}

async function removeSession(sessionId: string) {
	await deleteAISession(sessionId)
	if (currentSessionId.value === sessionId) {
		newConversation()
	}
	await loadSessions()
}

function handleKeyDown(e: KeyboardEvent) {
	if (e.key === 'Enter' && !e.shiftKey && canSubmitChat.value) {
		e.preventDefault()
		submitChat()
	}
}

loadSessions()
</script>

<template>
	<div class="flex w-full h-full flex-col overflow-hidden bg-gray-50">
		<div class="border-b bg-white px-5 py-4">
			<div class="flex items-center gap-3">
				<FeatherIcon name="zap" class="h-6 w-6 text-amber-500" />
				<div>
					<h1 class="text-xl font-bold text-gray-900">AI Query Builder</h1>
					<p class="text-sm text-gray-500">Build and refine queries with chat</p>
				</div>
			</div>
		</div>

		<div
			v-if="error"
			class="border-l-4 border-red-500 bg-red-50 px-4 py-3 text-sm text-red-700"
		>
			{{ error }}
		</div>

		<div class="flex flex-1 flex-col overflow-hidden lg:flex-row">
			<div class="flex min-h-0 flex-1 overflow-hidden flex-col bg-white lg:border-r">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<div>
						<p class="text-sm font-medium text-gray-900">Query Builder</p>
						<p class="text-xs text-gray-500">
							{{ query.doc.operations?.length || 0 }} operations generated
						</p>
					</div>
					<Badge variant="subtle" theme="blue">
						{{ selectedSession?.dataSource || selectedDataSource }}
					</Badge>
				</div>

				<div v-if="query.doc.operations?.length" class="flex min-h-0 flex-1 flex-col p-4">
					<QueryBuilderToolbar></QueryBuilderToolbar>
					<div class="mt-3 flex min-h-0 flex-1 flex-col gap-3 xl:flex-row">
						<div class="flex min-h-0 flex-1 overflow-hidden rounded border">
							<QueryDataTable
								:query="query"
								:enable-sort="true"
								:enable-drill-down="true"
							/>
						</div>
						<div
							class="flex min-h-[16rem] overflow-y-auto rounded border bg-white xl:min-h-0 xl:w-[20rem]"
						>
							<QueryOperations />
						</div>
					</div>
				</div>

				<div v-else class="flex flex-1 items-center justify-center p-6 text-gray-400">
					<div class="text-center">
						<FeatherIcon name="database" class="mx-auto h-12 w-12 text-gray-300" />
						<p class="mt-3 text-sm">
							Generate a query from chat to populate the builder
						</p>
					</div>
				</div>
			</div>

			<div class="flex min-h-0 flex-col bg-white lg:flex-shrink-0 lg:w-[22rem]">
				<div class="space-y-3 border-b px-4 py-3">
					<div class="flex items-center justify-between gap-2">
						<p class="text-sm font-medium text-gray-900">Chat</p>
						<Button size="sm" variant="ghost" @click="newConversation">
							New Session
						</Button>
					</div>

					<FormControl
						label="Data Source"
						type="select"
						:options="getDataSourceOptions()"
						v-model="selectedDataSource"
						:disabled="hasActiveSession"
					/>

					<div class="flex items-center gap-2">
						<FormControl
							type="select"
							class="min-w-0 flex-1"
							:options="sessionOptions"
							:modelValue="selectedSession"
							@update:modelValue="onSessionSelect"
							:placeholder="
								loadingSessions
									? 'Loading conversations...'
									: 'Open previous conversation'
							"
							:disabled="loadingSessions || sessionOptions.length === 0"
						>
							<template #prefix>
								<FeatherIcon name="message-circle" class="h-4 w-4 text-gray-500" />
							</template>
						</FormControl>
						<Button
							variant="ghost"
							size="sm"
							:loading="loadingSessions"
							@click="loadSessions"
						>
							<FeatherIcon name="refresh-cw" class="h-4 w-4 text-gray-500" />
						</Button>
						<Dropdown
							v-if="selectedSession"
							:options="[
								{
									label: 'Delete',
									onClick: () => removeSession(selectedSession!.value),
								},
							]"
						>
							<Button variant="ghost" size="sm">
								<FeatherIcon name="trash-2" class="h-4 w-4 text-gray-500" />
							</Button>
						</Dropdown>
					</div>
					<p
						v-if="!loadingSessions && sessionOptions.length === 0"
						class="text-xs text-gray-500"
					>
						No previous conversations yet.
					</p>
				</div>

				<div class="flex min-h-0 flex-1 flex-col overflow-hidden">
					<div class="flex-1 overflow-y-auto p-4">
						<div
							v-if="!hasMessages"
							class="flex h-full items-center justify-center text-gray-400"
						>
							<div class="text-center">
								<FeatherIcon
									name="message-circle"
									class="mx-auto h-10 w-10 text-gray-300"
								/>
								<p class="mt-2 text-sm">Ask your first question to start</p>
							</div>
						</div>

						<div v-else class="space-y-4">
							<div
								v-for="(msg, idx) in messages"
								:key="idx"
								:class="[
									'flex',
									msg.role === 'user' ? 'justify-end' : 'justify-start',
								]"
							>
								<div
									:class="[
										'max-w-[86%] rounded-2xl px-3 py-2.5',
										msg.role === 'user'
											? 'bg-gray-900 text-white'
											: 'bg-gray-100 text-gray-900',
									]"
								>
									<p class="text-sm">{{ msg.content }}</p>
									<div v-if="msg.operations" class="mt-2">
										<button
											@click="applyOperations(msg.operations)"
											class="text-xs underline opacity-80 hover:opacity-100"
										>
											Apply this query
										</button>
									</div>
									<div
										v-if="msg.error"
										class="mt-2 rounded bg-red-500/20 p-2 text-xs"
									>
										{{ msg.error }}
									</div>
								</div>
							</div>
						</div>
					</div>

					<div class="border-t bg-white p-3">
						<div v-if="generating" class="mb-2 flex items-center gap-2 text-gray-500">
							<LoadingIndicator class="h-4 w-4" />
							<span class="text-sm">AI is thinking...</span>
						</div>
						<div class="flex items-end gap-2">
							<TextInput
								v-if="hasActiveSession"
								v-model="followUpQuestion"
								placeholder="Ask follow-ups: add filter, sort, group, top N..."
								:rows="3"
								@keydown="handleKeyDown"
							/>
							<TextInput
								v-else
								v-model="currentQuestion"
								placeholder="e.g. Show monthly sales by region for this year"
								:rows="3"
								@keydown="handleKeyDown"
							/>
							<Button
								:loading="generating"
								:disabled="!canSubmitChat"
								@click="submitChat"
								variant="solid"
							>
								{{ hasActiveSession ? 'Send' : 'Generate' }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
