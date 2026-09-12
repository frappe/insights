<script setup lang="ts">
import { BookOpen, Braces, Bug, Play } from 'lucide-vue-next'
import { h, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import VariablesDialog from '../../components/VariablesDialog.vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import { attachRealtimeListener, wheneverChanges } from '../../helpers'
import session from '../../session'
import { __ } from '../../translation'
import { Query } from '../query'
import QueryActions from './QueryActions.vue'
import QueryDataTable from './QueryDataTable.vue'
import QueryHeader from './QueryHeader.vue'

const query = inject<Query>('query')!
const $find = ref<HTMLElement>()
query.autoExecute = false
query.ensureResult()

const operation = query.getCodeOperation()
const code = ref(operation ? operation.code : '')
wheneverChanges(code, () => query.setCode({ code: code.value }), { debounce: 500 })

const placeholder_script = `# assign rows to \`results\`, e.g. results = frappe.db.get_all("ToDo", fields=["name", "status"])`

const showLogs = ref(false)
const scriptLogs = ref<string[]>([])
attachRealtimeListener('insights_script_log', (data: any) => {
	if (data.user == session.user.email) {
		scriptLogs.value = data.logs
	}
})

// the error is written to the logs, so a failed run has to open the panel
// holding it - otherwise the script author is told nothing at all
wheneverChanges(
	() => query.executionError,
	(error) => {
		if (error) showLogs.value = true
	},
)

const DOCS_URL = 'https://docs.frappe.io/insights/querying/script-query-api'

function openDocs() {
	window.open(DOCS_URL, '_blank', 'noopener')
}

const showVariablesDialog = ref(false)
const localVariables = ref<any[]>([])

function openVariablesDialog() {
	localVariables.value = [...(query.doc.variables || [])]
	showVariablesDialog.value = true
}

const icon = (component: any) =>
	h(component, { class: 'h-3.5 w-3.5 text-ink-gray-6', strokeWidth: 1.5 })

const extraActions = () => [
	{ label: __('Force Run'), icon: icon(Play), onClick: () => query.execute(true) },
	{ label: __('Variables'), icon: icon(Braces), onClick: openVariablesDialog },
	{ label: __('Logs'), icon: icon(Bug), onClick: () => (showLogs.value = !showLogs.value) },
	{ label: __('Docs'), icon: icon(BookOpen), onClick: openDocs },
]

function handleSaveVariables(variables: any[]) {
	query
		.updateVariables(variables)
		.then(() => {
			showVariablesDialog.value = false
		})
		.catch((error) => {})
}
</script>

<template>
	<div class="flex flex-1 flex-col gap-3 overflow-hidden px-4 pb-4 pt-3">
		<QueryHeader>
			<QueryActions
				:on-execute="() => query.execute()"
				:extra-actions="extraActions"
				:stale="query.isStale"
			/>
		</QueryHeader>

		<div class="relative flex h-[55%] w-full flex-col overflow-hidden rounded-4 border">
			<div class="flex flex-1 overflow-hidden">
				<div class="flex-1">
					<Code v-model="code" language="python" :placeholder="placeholder_script" />
				</div>

				<transition
					tag="div"
					name="slide"
					enter-active-class="transition ease-out duration-200"
					enter-from-class="transform translate-x-full opacity-0"
					enter-to-class="transform translate-x-0 opacity-100"
					leave-active-class="transition ease-in duration-200"
					leave-from-class="transform translate-x-0"
					leave-to-class="transform translate-x-full"
				>
					<div
						v-if="showLogs"
						class="flex h-full w-[30rem] flex-shrink-0 flex-col overflow-hidden bg-surface-gray-1 p-3"
					>
						<div class="font-mono text-sm uppercase text-ink-gray-5">
							{{ __('Logs') }}
						</div>
						<div class="mt-2 flex w-full flex-col gap-2 overflow-y-auto font-mono">
							<div v-for="(log, index) in scriptLogs" :key="index" class="flex gap-2">
								<div class="text-ink-gray-3">[{{ index + 1 }}]</div>
								<div class="text-ink-gray-4">{{ log }}</div>
							</div>
						</div>
					</div>
				</transition>
			</div>
		</div>

		<div ref="$find" class="flex flex-shrink-0"></div>
		<ResultPane :query="query" :stale="query.isStale" :find-target="$find">
			<template #grid="{ rows, currentPage, pageSize }">
				<QueryDataTable
					:query="query"
					:rows="rows"
					:current-page="currentPage"
					:page-size="pageSize"
				/>
			</template>
		</ResultPane>
	</div>
	<VariablesDialog
		v-model:show="showVariablesDialog"
		v-model:variables="localVariables"
		@save="handleSaveVariables"
	/>
</template>
