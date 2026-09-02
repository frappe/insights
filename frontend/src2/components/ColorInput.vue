<template>
	<ColorPicker :modelValue="value" @update:modelValue="handleColorChange" :placement="placement">
		<template #target="{ togglePopover }">
			<TextInput
				type="text"
				class="w-full"
				placeholder="Select Color"
				:modelValue="value"
				@update:modelValue="handleColorChange"
			>
				<template #prefix>
					<!-- .stop, or the click also reaches the popover trigger wrapping
					     this input and toggles straight back. -->
					<div
						class="ml-2 h-4 w-4 rounded-4 shadow-sm"
						@click.stop="togglePopover"
						:style="{ background: value || unsetSwatch }"
					></div>
				</template>
				<template #suffix>
					<Button
						v-show="value"
						class="mr-1"
						variant="ghost"
						size="sm"
						icon="lucide-x"
						@click.stop="clearValue"
					/>
				</template>
			</TextInput>
		</template>
	</ColorPicker>
</template>

<script setup>
import { Button, TextInput } from 'frappe-ui'
import { computed } from 'vue'
import { getRGB } from '../charts/colors'
import ColorPicker from './ColorPicker.vue'

// Shown when no color is set: an RGB wash, so the swatch reads as "unset"
// rather than as a real color the user picked.
const unsetSwatch = `linear-gradient(217deg, rgba(255,0,0,.8), rgba(255,0,0,0) 70.71%),
	linear-gradient(127deg, rgba(0,255,0,.8), rgba(0,255,0,0) 70.71%),
	linear-gradient(336deg, rgba(0,0,255,.8), rgba(0,0,255,0) 70.71%)`

const props = defineProps({ modelValue: String, placement: String })
const emit = defineEmits(['update:modelValue'])

const value = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const handleColorChange = (v) => {
	value.value = getRGB(v)
}
const clearValue = () => {
	value.value = ''
}
</script>
