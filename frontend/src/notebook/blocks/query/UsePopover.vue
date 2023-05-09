<script setup>
import { slideDownTransition } from '@/utils/transitions'
import { createPopper } from '@popperjs/core'
import { whenever } from '@vueuse/core'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: Boolean,
	placement: { type: String, default: 'bottom-start' },
	targetElement: { type: Object, required: true },
	transition: { type: Object, default: slideDownTransition },
})

const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

if (!document.getElementById('frappeui-popper-root')) {
	const root = document.createElement('div')
	root.id = 'frappeui-popper-root'
	document.body.appendChild(root)
}

let popper = null
const popover = ref(null)
onMounted(() => {
	if (!props.targetElement) {
		console.warn('Popover: targetElement is required')
		return
	}
	popper = createPopper(props.targetElement, popover.value, {
		placement: props.placement,
		modifiers: [
			{
				name: 'offset',
				options: {
					offset: [0, 8],
				},
			},
		],
	})
	updatePosition()
	window.addEventListener('resize', updatePosition)
	window.addEventListener('scroll', updatePosition)

	if (props.targetElement) {
		props.targetElement.addEventListener('click', () => {
			toggle()
		})
	}
})
const updatePosition = () => show.value && popper?.update()
const toggle = () => (show.value = !show.value)
whenever(show, updatePosition)
onBeforeUnmount(() => {
	popper?.destroy()
	window.removeEventListener('resize', updatePosition)
	window.removeEventListener('scroll', updatePosition)
	if (props.targetElement) {
		props.targetElement.removeEventListener('click', toggle)
	}
})
</script>

<template>
	<teleport to="#frappeui-popper-root">
		<div ref="popover">
			<transition v-bind="transition">
				<div v-show="show">
					<slot></slot>
				</div>
			</transition>
		</div>
	</teleport>
</template>
