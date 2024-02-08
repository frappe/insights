<script setup>
import ContentEditable from '@/components/ContentEditable.vue'
import { watchDebounced } from '@vueuse/core'
import { ComponentIcon } from 'lucide-vue-next'
import { inject, ref } from 'vue'

const query = inject('query')
const title = ref(query.doc.title)
watchDebounced(title, query.updateTitle, { debounce: 500 })
</script>

<template>
	<div v-if="query.doc.is_stored" class="mr-1">
		<ComponentIcon class="h-4 w-4 text-gray-600" fill="currentColor" />
	</div>
	<ContentEditable
		v-model="title"
		placeholder="Untitled Query"
		class="mr-3 rounded-sm px-1 text-lg font-medium focus:ring-2 focus:ring-gray-700 focus:ring-offset-2"
	></ContentEditable>
	<div v-if="query.loading" class="flex items-center gap-1 text-sm text-gray-600">
		<LoadingIndicator class="w-3" />
		<span>Saving...</span>
	</div>
</template>
