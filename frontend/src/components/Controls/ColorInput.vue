<template>
	<ColorPicker :modelValue="value" @update:modelValue="handleColorChange" :placement="placement">
		<template #target="{ togglePopover }">
			<div class="relative flex items-center justify-between">
				<div
					class="absolute left-2 top-[6px] z-10 h-4 w-4 rounded shadow-sm"
					@click="togglePopover"
					:style="{
						background: value
							? value
							: `linear-gradient(217deg, rgba(255,0,0,.8), rgba(255,0,0,0) 70.71%),
									linear-gradient(127deg, rgba(0,255,0,.8), rgba(0,255,0,0) 70.71%),
									linear-gradient(336deg, rgba(0,0,255,.8), rgba(0,0,255,0) 70.71%)`,
					}"
				></div>
				<Input
					type="text"
					class="dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:focus:bg-zinc-700 w-full rounded-md text-sm text-gray-700"
					placeholder="Select Color"
					inputClass="pl-8 pr-6"
					:modelValue="value"
					@update:modelValue="handleColorChange"
				></Input>
				<div
					class="dark:text-zinc-300 absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700"
					@click="clearValue"
					v-show="value"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="14"
						height="14"
						viewBox="0 0 24 24"
					>
						<path
							fill="currentColor"
							d="M18.3 5.71a.996.996 0 0 0-1.41 0L12 10.59L7.11 5.7A.996.996 0 1 0 5.7 7.11L10.59 12L5.7 16.89a.996.996 0 1 0 1.41 1.41L12 13.41l4.89 4.89a.996.996 0 1 0 1.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4z"
						/>
					</svg>
				</div>
			</div>
		</template>
	</ColorPicker>
</template>

<script setup>
import { getRGB } from '@/utils/colors'
import { computed } from 'vue'
import ColorPicker from './ColorPicker.vue'

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
