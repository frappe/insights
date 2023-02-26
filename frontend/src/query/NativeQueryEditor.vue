<script setup>
import Code from '@/components/Controls/Code.vue'
import { inject, ref } from 'vue'

const query = inject('query')
const nativeQuery = ref(query.doc.sql)
function runQuery() {
	query.setValue.submit({ sql: nativeQuery.value }).then(() => {
		query.run.submit()
	})
}
function formatQuery() {
	query.setValue.submit({ sql: nativeQuery.value })
}
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col py-3">
		<div class="h-8 text-sm uppercase tracking-wide text-gray-600">Native Query</div>
		<Code v-model="nativeQuery" language="sql"></Code>
		<div class="mt-4 h-10 space-x-2">
			<Button iconLeft="play" appearance="white" class="shadow-sm" @click="runQuery">
				Run
			</Button>
			<Button iconLeft="loader" appearance="white" class="shadow-sm" @click="formatQuery">
				Format
			</Button>
		</div>
	</div>
</template>
