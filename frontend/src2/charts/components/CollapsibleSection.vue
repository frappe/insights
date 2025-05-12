<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'
import { ref } from 'vue'

const props = defineProps<{ title: string; collapsed?: boolean }>()

const collapsed = ref(props.collapsed ?? false)
</script>

<template>
	<div class="flex flex-col" :class="collapsed ? '' : 'pb-3.5'">
		<button
			class="sticky top-0 flex cursor-pointer items-center gap-1 bg-white py-3"
			@click="collapsed = !collapsed"
		>
			<div class="flex items-center gap-1">
				<slot name="title-prefix" />
				<p class="text-sm font-medium">
					{{ props.title }}
				</p>
				<slot name="title-suffix" />
			</div>
			<ChevronRight
				class="h-4 w-4 text-gray-700 transition-all"
				:class="{ 'rotate-90 transform': !collapsed }"
				stroke-width="1.5"
			/>
		</button>
		<slot v-if="!collapsed" />
	</div>
</template>
