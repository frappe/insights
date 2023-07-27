<script setup>
import { onMounted, ref, onBeforeUnmount, computed } from 'vue'
import UsePopover from './UsePopover.vue'
const props = defineProps({
	content: { type: String, default: null },
	targetElement: { type: Object, required: true },
	placement: { type: String, default: 'top' },
	hoverDelay: { type: Number, default: 0.5 },
})

const popover = ref(null)

let openTimer = null
let closeTimer = null
const listeners = {
	mouseenter: () => {
		closeTimer && (closeTimer = clearTimeout(closeTimer)) // clear and reset the timer
		openTimer = setTimeout(() => popover.value.open(), props.hoverDelay * 1000)
	},
	mouseleave: () => {
		openTimer && (openTimer = clearTimeout(openTimer)) // clear and reset the timer
		closeTimer = setTimeout(() => popover.value.close(), props.hoverDelay * 1000)
	},
}
const isVisible = computed(() => popover.value?.isOpen)
onMounted(() => {
	props.targetElement.addEventListener('mouseenter', listeners.mouseenter)
	props.targetElement.addEventListener('mouseleave', listeners.mouseleave)
})
onBeforeUnmount(() => {
	props.targetElement.removeEventListener('mouseenter', listeners.mouseenter)
	props.targetElement.removeEventListener('mouseleave', listeners.mouseleave)
})
</script>

<template>
	<UsePopover ref="popover" :targetElement="props.targetElement" :placement="props.placement">
		<slot name="content" v-bind="{ visible: isVisible }">
			<div
				v-if="props.content"
				class="z-10 rounded border border-gray-100 bg-gray-800 px-2 py-1 text-xs text-white shadow-xl"
			>
				{{ props.content }}
			</div>
		</slot>
	</UsePopover>
</template>
