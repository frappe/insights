<script setup lang="ts">
import { QueryResultColumn } from '../../types/query.types'

const emit = defineEmits({
	sort: (value: 'asc' | 'desc' | '') => true,
})
const props = defineProps<{ column: QueryResultColumn }>()
</script>

<template>
	<div class="flex flex-col">
		<Button
			variant="ghost"
			class="w-full !justify-start"
			icon-left="arrow-up"
			@click="emit('sort', 'asc')"
		>
			<span class="truncate">Ascending</span>
		</Button>
		<Button
			variant="ghost"
			class="w-full !justify-start"
			icon-left="arrow-down"
			@click="emit('sort', 'desc')"
		>
			<span class="truncate">Descending</span>
		</Button>
		<Button
			variant="ghost"
			class="w-full !justify-start"
			icon-left="x"
			@click="emit('sort', '')"
		>
			<span class="truncate">Remove Sort</span>
		</Button>
	</div>
</template>
