<script setup lang="ts">
import Checkbox from '@/components/Controls/Checkbox.vue'
import DraggableList from '@/components/DraggableList.vue'
import { BoxSelectIcon, CheckSquare, ColumnsIcon, LayoutList, ListChecks } from 'lucide-vue-next'
import { inject } from 'vue'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline
</script>

<template>
	<Popover placement="bottom-start">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				size="lg"
				class="rounded-none"
				:class="{ 'bg-gray-100': isOpen }"
				@click="togglePopover"
			>
				<template #icon>
					<ColumnsIcon class="h-5 w-5 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<div class="flex flex-col p-2">
				<!-- select all -->
				<div class="mb-2 flex items-center gap-1">
					<Checkbox
						class="flex-1"
						:label="'Select all'"
						:modelValue="true"
						:size="'sm'"
					/>
				</div>

				<DraggableList
					:items="queryPipeline.results.columns"
					empty-text="No columns selected"
					group="columns"
					@update:items="() => {}"
				>
					<template #item="{ item: column }">
						<Checkbox :label="column.name" :modelValue="true" :size="'sm'" />
					</template>
				</DraggableList>
			</div>
		</template>
	</Popover>
</template>
