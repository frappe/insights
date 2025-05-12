<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { CheckSquare, SearchIcon, Square } from 'lucide-vue-next'
import { ref } from 'vue'

const props = defineProps<{
	valuesProvider: (search: string) => Promise<string[]>
}>()
const selectedValues = defineModel<string[]>({
	type: Array,
	default: () => [],
})

const distinctColumnValues = ref<any[]>([])
const searchInput = ref('')
const fetchingValues = ref(false)
watchDebounced(
	() => searchInput.value,
	(searchTxt) => {
		fetchingValues.value = true
		props
			.valuesProvider(searchTxt)
			.then((values: string[]) => (distinctColumnValues.value = values))
			.finally(() => (fetchingValues.value = false))
	},
	{ debounce: 300, immediate: true }
)

function toggleValue(value: string) {
	if (selectedValues.value.includes(value)) {
		selectedValues.value = selectedValues.value.filter((v) => v !== value)
	} else {
		selectedValues.value = [...selectedValues.value, value]
	}
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<FormControl placeholder="Search" v-model="searchInput" autocomplete="off">
			<template #prefix>
				<SearchIcon class="h-4 w-4 text-gray-400" />
			</template>
			<template #suffix>
				<LoadingIndicator v-if="fetchingValues" class="h-4 w-4 text-gray-600" />
			</template>
		</FormControl>
		<div class="max-h-[10rem] overflow-y-scroll">
			<div
				v-for="(value, idx) in distinctColumnValues.slice(0, 50)"
				:key="value || idx"
				class="flex cursor-pointer items-center justify-between gap-2 rounded px-1 py-1.5 text-base hover:bg-gray-100"
				@click.prevent.stop="toggleValue(value)"
			>
				<component
					:is="selectedValues.includes(value) ? CheckSquare : Square"
					class="h-4 w-4 text-gray-600"
				/>
				<span class="flex-1 truncate"> {{ value }} </span>
			</div>
		</div>
	</div>
</template>
