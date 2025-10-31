<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { ArrowDownAZ, ArrowUpAZ, CheckSquare, SearchIcon, Square } from 'lucide-vue-next'
import { computed, ref } from 'vue'

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
const sortOrder = ref<'asc' | 'desc'>('asc')

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

const sortedValues = computed(() => {
  const values = [...distinctColumnValues.value];
  const order = sortOrder.value === 'asc' ? 1 : -1;
  
  return values.sort((a, b) => {
    const stringA = String(a);
    const stringB = String(b);
    
    // try numeric comparison first
    const numA = Number(stringA);
    const numB = Number(stringB);
    
    if (!isNaN(numA) && !isNaN(numB) && stringA.trim() && stringB.trim()) {
      return (numA - numB) * order;
    }
    
    return stringA.toLowerCase().localeCompare(stringB.toLowerCase(), undefined, { numeric: true }) * order;
  });
});

function toggleValue(value: string) {
	if (selectedValues.value.includes(value)) {
		selectedValues.value = selectedValues.value.filter((v) => v !== value)
	} else {
		selectedValues.value = [...selectedValues.value, value]
	}
}

function toggleSort() {
	sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center gap-2">
			<FormControl
				placeholder="Search"
				v-model="searchInput"
				autocomplete="off"
				class="flex-1"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-400" />
				</template>
				<template #suffix>
					<LoadingIndicator v-if="fetchingValues" class="h-4 w-4 text-gray-600" />
				</template>
			</FormControl>
			<button
				@click.stop="toggleSort"
				class="flex h-7 w-7 items-center justify-center rounded border border-gray-300 bg-white hover:bg-gray-50"
				:title="sortOrder === 'asc' ? 'Sort descending' : 'Sort ascending'"
			>
				<component :is="sortOrder === 'asc' ? ArrowDownAZ : ArrowUpAZ" class="h-4 w-4" />
			</button>
		</div>
		<div class="max-h-[10rem] overflow-y-scroll">
			<div
				v-for="(value, idx) in sortedValues.slice(0, 50)"
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
