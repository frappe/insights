<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { slideRightTransition } from '@/utils/transitions'
const props = defineProps({
	blockRef: Object,
	actions: {
		type: Array,
		default: () => [],
	},
})
</script>

<template>
	<UsePopover
		v-if="blockRef"
		:targetElement="blockRef"
		placement="right-start"
		:transition="slideRightTransition"
	>
		<div class="flex w-[10rem] flex-col space-y-1.5 text-sm transition-all">
			<slot />
		</div>
	</UsePopover>
</template>
