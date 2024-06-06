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
	itemClick: (idx: number) => void
}>()
</script>

<template>
	<div class="flex flex-col gap-2 px-2.5 py-2">
		<div class="flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-[11px] uppercase">{{ section.title }}</div>
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
		<div v-else class="flex flex-col gap-1.5">
			<button
				v-for="(row, idx) in section.items"
				:key="row[section.itemKey]"
				@click="section.itemClick(idx)"
				class="group flex w-full cursor-pointer items-center justify-between rounded border border-gray-300 p-0.5 pl-1.5 text-sm transition-all hover:border-gray-400"
				:class="
					section.isActive(idx)
						? 'border-gray-700 hover:border-gray-700'
						: 'border-gray-200'
				"
			>
				<div class="flex gap-1.5">
					<slot name="item-icon" :item="row" />
					<p>{{ row.name }}</p>
				</div>
				<button
					class="invisible cursor-pointer rounded p-1 transition-all hover:bg-gray-100 group-hover:visible"
					@click.prevent.stop="section.remove(row)"
				>
					<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</button>
			</button>
		</div>
	</div>
</template>
