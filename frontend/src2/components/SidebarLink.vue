<template>
	<button
		class="flex h-7 cursor-pointer items-center rounded text-gray-800 duration-300 ease-in-out focus:outline-none focus:transition-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-gray-400"
		:class="isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100'"
		@click="handleClick"
	>
		<div
			class="flex items-center duration-300 ease-in-out"
			:class="isCollapsed ? 'p-1' : 'px-2 py-1'"
		>
			<Tooltip :text="label" placement="right">
				<slot name="icon">
					<component :is="icon" class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</slot>
			</Tooltip>
			<span
				class="flex-shrink-0 truncate text-base duration-300 ease-in-out"
				:class="
					isCollapsed ? 'ml-0 w-0 overflow-hidden opacity-0' : 'ml-2 w-auto opacity-100'
				"
			>
				{{ label }}
			</span>
		</div>
	</button>
</template>

<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const props = defineProps<{
	icon?: any
	label: string
	to?: string
	isCollapsed?: boolean
}>()

function handleClick() {
	router.push({ name: props.to })
}

let isActive = computed(() => {
	return router.currentRoute.value.name === props.to
})
</script>
