<script setup>
import useMarketplaceStore from '@/stores/marketplaceStore'
import { ArrowLeft } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import TemplateSingle from './TemplateSingle.vue'
import TemplatesGrid from './TemplatesGrid.vue'

const currentTemplate = ref(null)
const marketplaceStore = useMarketplaceStore()
const search = ref('')
const filteredTemplates = computed(() => {
	return marketplaceStore.allTemplates?.filter((template) => {
		return template.title.toLowerCase().includes(search.value.toLowerCase())
	})
})
</script>

<template>
	<div class="flex min-h-0 flex-col space-y-4 p-5">
		<template v-if="!currentTemplate">
			<div class="flex items-center justify-between">
				<h2 class="font-bold leading-none">Browse Templates</h2>
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
			<TemplatesGrid
				:templates="filteredTemplates"
				:show-status="false"
				@select="(template) => (currentTemplate = template)"
			/>
		</template>

		<template v-else-if="currentTemplate">
			<div>
				<Button variant="ghost" @click="currentTemplate = null">
					<template #prefix>
						<ArrowLeft class="h-4 w-4" />
					</template>
					<span>Back to Templates</span>
				</Button>
			</div>
			<TemplateSingle class="mt-4" :template="currentTemplate" />
		</template>
	</div>
</template>
