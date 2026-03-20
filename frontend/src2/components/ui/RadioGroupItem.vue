<template>
	<div class="relative flex items-start">
		<input
			:id="inputId"
			ref="inputRef"
			type="radio"
			:name="radioGroup?.name?.value"
			:value="value"
			:checked="isChecked"
			:disabled="isDisabled"
			:aria-describedby="describedBy"
			class="sr-only peer"
			@change="handleChange"
			v-bind="$attrs"
		/>
		<label
			:for="inputId"
			class="flex items-start gap-2 text-sm font-medium leading-none cursor-pointer"
			:class="{ 'cursor-not-allowed opacity-70': isDisabled }"
		>
			<span
				class="flex h-4 w-4 aspect-square items-center justify-center rounded-full border transition-colors duration-200 ease-in-out"
				:class="[
					isChecked ? 'border-black bg-black' : 'border-gray-300',
					isDisabled && 'border-gray-200 bg-gray-100',
				]"
			>
				<span
					class="h-2 w-2 rounded-full transition-opacity duration-200"
					:class="[
						isChecked ? 'opacity-100' : 'opacity-0',
						isDisabled && isChecked ? 'bg-gray-400' : 'bg-white',
					]"
				/>
			</span>
			<slot />
		</label>
	</div>
</template>

<script setup lang="ts">
import { inject, computed, ref } from 'vue'

interface Props {
	value: string
	disabled?: boolean
	id?: string
	describedBy?: string
}

const props = withDefaults(defineProps<Props>(), {
	disabled: false,
})

const radioGroup = inject<{
	modelValue: any
	name: any
	disabled: any
	updateValue: (value: string) => void
}>('radioGroup')

const inputRef = ref<HTMLInputElement>()
const inputId = computed(() => props.id || `radio-${Math.random().toString(36).substr(2, 9)}`)

const isChecked = computed(() => radioGroup?.modelValue?.value === props.value)
const isDisabled = computed(() => props.disabled || radioGroup?.disabled?.value)

const handleChange = () => {
	if (!isDisabled.value) {
		radioGroup?.updateValue(props.value)
	}
}

defineExpose({
	inputRef,
})
</script>
