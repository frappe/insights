<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
const section = defineProps<{
	title: string
	emptyMessage: string
	items: any[]
	itemKey: string
	isActive: (item: any) => boolean
	add: () => void
	remove: (item: any) => void
	route: (item: any) => string
}>()

function setDraggedItem(event: DragEvent, row: any) {
	if (!event.dataTransfer) return
	const data = JSON.stringify({ type: section.title, item: row })
	event.dataTransfer.setData('text/plain', data)
}
</script>

<template>
	<div class="flex flex-col px-3.5 pt-3">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm-medium">{{ section.title }}</div>
			</div>
			<div>
				<Button class="!h-fit !p-1" variant="ghost" @click="section.add()">
					<Plus class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</div>
		</div>
		<div
			v-if="!section.items.length"
			class="flex h-12 flex-col items-center justify-center rounded-4 border border-dashed border-outline-gray-2 py-2"
		>
			<div class="text-xs text-ink-gray-4">{{ section.emptyMessage }}</div>
		</div>
		<div v-else class="flex flex-col border-b pb-3">
			<div
				v-for="(row, idx) in section.items"
				:key="row[section.itemKey]"
				class="group w-full cursor-pointer rounded-4 transition-all hover:bg-surface-gray-2"
				:class="
					section.isActive(row) ? ' bg-surface-gray-2' : ' hover:border-outline-gray-2'
				"
				draggable="true"
				@dragstart="setDraggedItem($event, row)"
			>
				<router-link
					:to="route(row)"
					class="flex h-7.5 items-center justify-between rounded-4 pl-1.5 text-sm"
				>
					<div class="flex gap-1.5 overflow-hidden">
						<div class="flex-shrink-0">
							<slot name="item-icon" :item="row" />
						</div>
						<p class="truncate">{{ row.title }}</p>
					</div>
					<button
						class="invisible cursor-pointer rounded-4 px-1.5 py-1 transition-all hover:bg-surface-gray-2 group-hover:visible"
						@click.prevent.stop="section.remove(row)"
					>
						<X class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</button>
				</router-link>
			</div>
		</div>
	</div>
</template>
