<script setup lang="ts">
import { ArrowUpDown, ChevronRight } from 'lucide-vue-next'
import { QueryPipelineResultColumn } from '../useQueryPipeline'

const emit = defineEmits({
	sort: (value: 'asc' | 'desc' | '') => true,
})
const props = defineProps<{ column: QueryPipelineResultColumn }>()
</script>

<template>
	<Popover placement="right-start">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				@click="togglePopover"
				class="w-full !justify-start"
				:class="{ ' !bg-gray-100': isOpen }"
			>
				<template #icon>
					<div class="flex w-full items-center gap-2 px-1.5 text-base">
						<ArrowUpDown class="h-4 w-4 flex-shrink-0" />
						<div class="flex flex-1 items-center justify-between">
							<span class="truncate">Sort</span>
							<ChevronRight class="h-4 w-4" />
						</div>
					</div>
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover }">
			<div class="flex min-w-[10rem] flex-col p-1.5">
				<Button
					variant="ghost"
					class="w-full !justify-start"
					icon-left="arrow-up"
					@click=";[togglePopover(), emit('sort', 'asc')]"
				>
					<span class="truncate">Ascending</span>
				</Button>
				<Button
					variant="ghost"
					class="w-full !justify-start"
					icon-left="arrow-down"
					@click=";[togglePopover(), emit('sort', 'desc')]"
				>
					<span class="truncate">Descending</span>
				</Button>
				<Button
					variant="ghost"
					class="w-full !justify-start"
					icon-left="x"
					@click=";[togglePopover(), emit('sort', '')]"
				>
					<span class="truncate">Remove Sort</span>
				</Button>
			</div>
		</template>
	</Popover>
</template>
