<script setup>
import { inject, ref, watch } from 'vue'
import ResultSection from './ResultSection.vue'
import NativeQueryEditor from './NativeQueryEditor.vue'

const query = inject('query')
const nativeQuery = ref(query.doc.sql)
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<div class="flex-shrink-0 uppercase leading-7 tracking-wide text-gray-600">
			Native Query
		</div>
		<div class="flex flex-1 flex-shrink-0 overflow-hidden rounded border">
			<NativeQueryEditor />
		</div>
		<div class="flex w-full flex-1 flex-shrink-0 overflow-hidden rounded border py-4">
			<ResultSection></ResultSection>
		</div>
	</div>
</template>
