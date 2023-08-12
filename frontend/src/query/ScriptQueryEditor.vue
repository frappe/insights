<script setup>
import Code from '@/components/Controls/Code.vue'
import { Braces } from 'lucide-vue-next'
import { inject, ref, watch } from 'vue'
import VariablesDialog from './VariablesDialog.vue'

const query = inject('query')
const script = ref(query.doc.script)
watch(
	() => query.doc.script,
	(value) => (script.value = value)
)
function runQuery() {
	query.setValue.submit({ script: script.value }).then(() => {
		query.run.submit()
	})
}

const showVariablesDialog = ref(false)
function handleSaveVariables(variables) {
	query.setValue.submit({ variables })
	showVariablesDialog.value = false
}
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col">
		<div class="flex-shrink-0 text-sm uppercase leading-7 tracking-wide text-gray-600">
			Script Query
		</div>
		<div class="relative flex flex-1 flex-col overflow-y-scroll rounded border">
			<Code language="python" v-model="script" placeholder="Enter your script here...">
			</Code>
			<div class="sticky bottom-0 flex gap-2 bg-white p-2">
				<div>
					<Button variant="subtle" @click="showVariablesDialog = !showVariablesDialog">
						<template #icon>
							<Braces class="h-4 w-4" />
						</template>
					</Button>
				</div>
				<div>
					<Button
						variant="solid"
						icon="play"
						@click="runQuery"
						:loading="query.run.loading"
					>
					</Button>
				</div>
			</div>
		</div>
	</div>
	<VariablesDialog
		v-model:show="showVariablesDialog"
		v-model:variables="query.doc.variables"
		@save="handleSaveVariables"
	/>
</template>
