<script setup>
import { computed, ref } from 'vue'
import useTemplateStore from '@/stores/templateStore'
import TemplatesGrid from './TemplatesGrid.vue'

const templates = useTemplateStore()
const search = ref('')
const filteredTemplates = computed(() => {
	return templates.myTemplates?.filter((template) => {
		return template.title.toLowerCase().includes(search.value.toLowerCase())
	})
})
</script>

<template>
	<div class="flex min-h-0 flex-col space-y-4 p-5">
		<div class="flex items-center justify-between">
			<h2 class="text-xl font-bold leading-none">My Templates</h2>
			<div class="flex items-center gap-4">
				<Input
					icon-left="search"
					type="text"
					placeholder="Find by title"
					@input="search = $event"
					:debounce="300"
				/>
			</div>
		</div>
		<TemplatesGrid :templates="filteredTemplates" />
	</div>
</template>
