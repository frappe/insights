<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { Bug, Play, Braces } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import ContentEditable from '../../components/ContentEditable.vue'
import VariablesDialog from '../../components/VariablesDialog.vue'
import { attachRealtimeListener, wheneverChanges } from '../../helpers'
import session from '../../session'
import { Query } from '../query'
import QueryDataTable from './QueryDataTable.vue'

const query = inject<Query>('query')!
query.autoExecute = false
query.execute()

const operation = query.getCodeOperation()
const code = ref(operation ? operation.code : '')
wheneverChanges(code, () => query.setCode({ code: code.value }), { debounce: 500 })

const placeholder_script = `# Write your script here`

const showLogs = ref(false)
const scriptLogs = ref<string[]>([])
attachRealtimeListener('insights_script_log', (data: any) => {
	if (data.user == session.user.email) {
		scriptLogs.value = data.logs
	}
})

const showVariablesDialog = ref(false)
const localVariables = ref<any[]>([])

function openVariablesDialog() {
	localVariables.value = [...(query.doc.variables || [])]
	showVariablesDialog.value = true
}

function handleSaveVariables(variables: any[]) {
	query.updateVariables(variables).then(() => {
		showVariablesDialog.value = false
	}).catch((error) => {

	})
}
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
				<Button @click="query.execute" label="Run">
					<template #prefix>
						<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
				<Button @click="openVariablesDialog" label="Variables">
					<template #prefix>
						<Braces class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
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
			<QueryDataTable :query="query" :enable-alerts="true" />
		</div>
	</div>
	<VariablesDialog
		v-model:show="showVariablesDialog"
		v-model:variables="localVariables"
		@save="handleSaveVariables"
	/>
</template>
