<script setup>
import { slideDownTransition } from '@/utils/transitions'
import { createPopper } from '@popperjs/core'
import { whenever } from '@vueuse/core'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: { type: Boolean, default: undefined },
	placement: { type: String, default: 'bottom-start' },
	targetElement: { type: Object, required: true },
	transition: { type: Object, default: slideDownTransition },
	autoClose: { type: Boolean, default: true },
})

const showPropPassed = props.show !== undefined
const _show = ref(false)
const show = computed({
	get: () => (showPropPassed ? props.show : _show.value),
	set: (value) => (showPropPassed ? emit('update:show', value) : (_show.value = value)),
})

if (!document.getElementById('frappeui-popper-root')) {
	const root = document.createElement('div')
	root.id = 'frappeui-popper-root'
	document.body.appendChild(root)
}

let popper = null
const popover = ref(null)

const toggle = () => (show.value = !show.value)
const open = () => (show.value = true)
const close = () => (show.value = false)

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

	props.targetElement.addEventListener('click', open)
	props.targetElement.addEventListener('focus', open)

	if (props.autoClose) document.addEventListener('click', handleClickOutside)
})

const handleClickOutside = (e) => {
	const insidePopover = popover.value.contains(e.target)
	if (insidePopover) return
	const insideTarget = props.targetElement.contains(e.target)
	if (insideTarget) return
	const popoverRoot = document.getElementById('frappeui-popper-root')
	const insidePopoverRoot = popoverRoot.contains(e.target)
	if (insidePopoverRoot) return
	close()
}

const updatePosition = () => show.value && popper?.update()
whenever(show, updatePosition)

onBeforeUnmount(() => {
	popper?.destroy()
	window.removeEventListener('resize', updatePosition)
	window.removeEventListener('scroll', updatePosition)
	props.targetElement.removeEventListener('click', toggle)
	props.targetElement.removeEventListener('focus', open)
	if (props.autoClose) document.removeEventListener('click', handleClickOutside)
})

defineExpose({ toggle, open, close, isOpen: show })
</script>

<template>
	<teleport to="#frappeui-popper-root">
		<div ref="popover" class="z-[100]">
			<transition v-bind="transition">
				<div v-show="show">
					<slot v-bind="{ toggle }"> </slot>
				</div>
			</transition>
		</div>
	</teleport>
</template>
