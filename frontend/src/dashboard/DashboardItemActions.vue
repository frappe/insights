<script setup>
import { downloadImage } from '@/utils'
import { inject } from 'vue'

const props = defineProps({ item: Object })
const dashboard = inject('dashboard')
const widgetRef = inject('widgetRef')
const actions = [
	{
		icon: 'external-link',
		label: 'Open Query',
		hidden: (item) => item.item_type === 'Filter' || item.item_type === 'Text',
		onClick(item) {
			if (!item.options.query) return
			window.open(`/insights/query/build/${item.options.query}`, '_blank')
		},
	},
	{
		icon: 'download',
		label: 'Download',
		hidden: (item) => item.item_type === 'Filter' || item.item_type === 'Text',
		onClick() {
			downloadImage(widgetRef.value.$el, `${props.item.options.title}.png`)
		},
	},
	{
		icon: 'trash',
		label: 'Delete',
		onClick: (item) => dashboard.removeItem(item),
	},
]
</script>
<template>
	<div class="flex cursor-pointer rounded bg-gray-800 p-1 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="px-1 py-0.5"
			:class="{ hidden: action.hidden && action.hidden(item) }"
			@click="action.onClick(item)"
		>
			<FeatherIcon :name="action.icon" class="h-3.5 w-3.5 text-white" />
		</div>
	</div>
</template>
