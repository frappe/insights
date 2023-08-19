<script setup>
import Code from '@/components/Controls/Code.vue'
import { useStorage } from '@vueuse/core'
import { Braces, Bug } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'
import VariablesDialog from './VariablesDialog.vue'

const query = inject('query')
const script = ref(query.doc.script)
watch(
	() => query.doc.script,
	(value) => (script.value = value)
)
const executing = ref(false)
async function runQuery() {
	if (executing.value) return
	executing.value = true
	try {
		await query.setValue.submit({ script: script.value })
		await query.run.submit()
	} finally {
		executing.value = false
	}
}

const showVariablesDialog = ref(false)
function handleSaveVariables(variables) {
	query.setValue.submit({ variables })
	showVariablesDialog.value = false
}

const showLogs = useStorage(`query-${query.doc.name}-show-logs`, false)
const scriptLogs = computed(() => query.doc.script_log?.split('\n')?.slice(1))
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col">
		<div class="flex-shrink-0 text-sm uppercase leading-7 tracking-wide text-gray-600">
			Script Query
		</div>
		<div class="flex flex-1 overflow-hidden rounded border">
			<div class="relative flex flex-1 flex-col overflow-y-scroll">
				<Code language="python" v-model="script" placeholder="Enter your script here...">
				</Code>
				<div class="sticky bottom-0 flex gap-2 bg-white p-2">
					<Button variant="subtle" @click="showVariablesDialog = !showVariablesDialog">
						<template #icon>
							<Braces class="h-4 w-4" />
						</template>
					</Button>
					<Button variant="subtle" @click="showLogs = !showLogs">
						<template #icon>
							<Bug class="h-4 w-4" />
						</template>
					</Button>
					<Button variant="solid" icon="play" @click="runQuery" :loading="executing">
					</Button>
				</div>
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
					class="flex h-full w-[30rem] flex-col overflow-hidden bg-gray-50 p-3"
				>
					<div class="text-sm uppercase tracking-wide text-gray-600">Logs</div>
					<div class="mt-2 flex w-full flex-col gap-2 overflow-scroll font-mono">
						<div v-for="(log, index) in scriptLogs" :key="index" class="flex gap-2">
							<div class="text-gray-400">[{{ index + 1 }}]</div>
							<div class="text-gray-500">{{ log }}</div>
						</div>
					</div>
				</div>
			</transition>
		</div>
	</div>
	<VariablesDialog
		v-model:show="showVariablesDialog"
		v-model:variables="query.doc.variables"
		@save="handleSaveVariables"
	/>
</template>
