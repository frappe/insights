<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { Bug, Play, RefreshCw } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'
import ContentEditable from '../../components/ContentEditable.vue'
import { attachRealtimeListener } from '../../helpers'
import session from '../../session'

const query = inject<Query>('query')!
query.autoExecute = false

const operation = query.getCodeOperation()
const code = ref(operation ? operation.code : '')
function execute() {
	query.setCode({ code: code.value })
}

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() =>
	query.result.totalRowCount ? query.result.totalRowCount.toLocaleString() : ''
)

const placeholder_script = `# Write your script here`

const showLogs = ref(false)
const scriptLogs = ref<string[]>([])
attachRealtimeListener('insights_script_log', (data: any) => {
	if (data.user == session.user.email) {
		scriptLogs.value = data.logs
	}
})
</script>

<template>
	<div class="flex flex-1 flex-col gap-4 overflow-hidden p-4">
		<div class="relative flex h-[55%] w-full flex-col rounded border">
			<div class="flex flex-shrink-0 items-center gap-1 border-b p-1">
				<ContentEditable
					class="flex h-7 cursor-text items-center justify-center rounded bg-white px-2 text-base text-gray-800 focus-visible:ring-1 focus-visible:ring-gray-600"
					v-model="query.doc.title"
					placeholder="Untitled Dashboard"
				></ContentEditable>
			</div>
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
						class="flex h-full w-[30rem] flex-shrink-0 flex-col overflow-hidden bg-gray-50 p-3"
					>
						<div class="font-mono text-sm uppercase text-gray-600">Logs</div>
						<div class="mt-2 flex w-full flex-col gap-2 overflow-y-auto font-mono">
							<div v-for="(log, index) in scriptLogs" :key="index" class="flex gap-2">
								<div class="text-gray-400">[{{ index + 1 }}]</div>
								<div class="text-gray-500">{{ log }}</div>
							</div>
						</div>
					</div>
				</transition>
			</div>
			<div class="flex flex-shrink-0 gap-1 border-t p-1">
				<Button @click="execute" label="Run">
					<template #prefix>
						<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
				<Button @click="showLogs = !showLogs" label="Logs">
					<template #prefix>
						<Bug class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>

		<div
			v-show="query.result.executedSQL"
			class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
		>
			<div class="h-2 w-2 rounded-full bg-green-500"></div>
			<div>
				<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
				<span v-else> Fetched in {{ query.result.timeTaken }}s </span>
				<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
			</div>
		</div>

		<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded border">
			<div
				v-if="query.executing"
				class="absolute top-10 z-10 flex w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>

			<DataTable :columns="columns" :rows="rows" :on-export="query.downloadResults">
				<template #footer-left>
					<div class="tnum flex items-center gap-2 text-sm text-gray-600">
						<span> Showing {{ previewRowCount }} of </span>
						<span v-if="!totalRowCount" class="inline-block">
							<Tooltip text="Load Count">
								<RefreshCw
									v-if="!query.fetchingCount"
									class="h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
									stroke-width="1.5"
									@click="query.fetchResultCount"
								/>
								<LoadingIndicator v-else class="h-3.5 w-3.5 text-gray-600" />
							</Tooltip>
						</span>
						<span v-else> {{ totalRowCount }} </span>
						rows
					</div>
				</template>
			</DataTable>
		</div>
	</div>
</template>
