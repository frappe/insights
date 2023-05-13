<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { slideRightTransition } from '@/utils/transitions'
import BlockActionButton from './BlockActionButton.vue'
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
		<div class="flex w-[8rem] flex-col space-y-1.5 text-sm transition-all">
			<template v-for="(action, index) in actions" :key="index">
				<component v-if="action.component" :is="action.component" v-bind="action.props" />
				<BlockActionButton v-else v-bind="action" />
			</template>
		</div>
	</UsePopover>
</template>
