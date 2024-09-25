<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
const section = defineProps<{
	title: string
	emptyMessage: string
	items: any[]
	itemKey: string
	isActive: (idx: number) => boolean
	add: () => void
	remove: (item: any) => void
	route: (idx: number) => string
}>()

function setDraggedItem(event: DragEvent, row: any) {
	if (!event.dataTransfer) return
	const data = JSON.stringify({ type: section.title, item: row })
	event.dataTransfer.setData('text/plain', data)
}
</script>

<template>
	<div class="flex flex-col border-b px-3.5 py-3">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">{{ section.title }}</div>
			</div>
			<div>
				<button
					class="cursor-pointer rounded p-1 transition-colors hover:bg-gray-100"
					@click="section.add()"
				>
					<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</button>
			</div>
		</div>
		<div
			v-if="!section.items.length"
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
		>
			<div class="text-xs text-gray-500">{{ section.emptyMessage }}</div>
		</div>
		<div v-else class="flex flex-col">
			<div
				v-for="(row, idx) in section.items"
				:key="row[section.itemKey]"
				class="group w-full cursor-pointer rounded transition-all hover:bg-gray-50"
				:class="section.isActive(idx) ? ' bg-gray-100' : ' hover:border-gray-300'"
				draggable="true"
				@dragstart="setDraggedItem($event, row)"
			>
				<router-link
					:to="route(idx)"
					class="flex h-7.5 items-center justify-between rounded pl-1.5 text-sm"
				>
					<div class="flex gap-1.5">
						<slot name="item-icon" :item="row" />
						<p>{{ row.title }}</p>
					</div>
					<button
						class="invisible cursor-pointer rounded p-1 transition-all hover:bg-gray-100 group-hover:visible"
						@click.prevent.stop="section.remove(row)"
					>
						<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</button>
				</router-link>
			</div>
		</div>
	</div>
</template>
