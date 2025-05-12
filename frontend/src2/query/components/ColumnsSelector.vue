<script setup lang="ts">
import DraggableList from '../../components/DraggableList.vue'
import { ColumnsIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { Query } from '../query'

const query = inject('query') as Query
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
					<Toggle class="flex-1" :label="'Select all'" :modelValue="true" :size="'sm'" />
				</div>

				<DraggableList
					:items="query.result.columns"
					empty-text="No columns selected"
					group="columns"
					@update:items="() => {}"
				>
					<template #item="{ item: column }">
						<Toggle :label="column.name" :modelValue="true" :size="'sm'" />
					</template>
				</DraggableList>
			</div>
		</template>
	</Popover>
</template>
