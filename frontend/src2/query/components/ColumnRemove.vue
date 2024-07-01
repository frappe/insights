<script setup lang="ts">
import { Trash } from 'lucide-vue-next'
import { QueryResultColumn } from '../../types/query.types'

const emit = defineEmits(['remove'])

const props = defineProps<{ column: QueryResultColumn }>()
</script>

<template>
	<Button theme="red" variant="ghost" @click="emit('remove')" class="w-full !justify-start">
		<template #icon>
			<div class="flex h-7 w-full items-center gap-2 pl-2 pr-1.5 text-base">
				<Trash class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
				<div class="flex flex-1 items-center justify-between">
					<span class="truncate">Remove</span>
				</div>
			</div>
		</template>
	</Button>
</template>
