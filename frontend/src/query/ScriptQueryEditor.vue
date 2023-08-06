<script setup>
import Code from '@/components/Controls/Code.vue'
import { inject, ref, watch } from 'vue'

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
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col">
		<div class="flex-shrink-0 text-sm uppercase leading-7 tracking-wide text-gray-600">
			Script Query
		</div>
		<div class="flex flex-1 overflow-y-scroll rounded border p-2">
			<Code language="python" v-model="script" placeholder="Enter your script here...">
			</Code>
		</div>
		<div class="mt-2 flex-shrink-0 space-x-2">
			<Button
				iconLeft="play"
				variant="outline"
				@click="runQuery"
				:loading="query.run.loading"
			>
				Run
			</Button>
		</div>
	</div>
</template>
