<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Autocomplete } from 'frappe-ui'
import { __ } from '../../translation'
import type { Preset } from '../../types/query.types'
import { findPresetByValue } from './filter_utils'

const props = defineProps<{
	presets: Preset[]
}>()

const modelValue = defineModel<any>()

const isCustom = ref(false)

const currentPresetMatch = computed(() => {
	return findPresetByValue(props.presets, modelValue.value)
})

function selectPreset(preset: Preset) {
	isCustom.value = false
	modelValue.value = preset.value()
}

watch(
	() => modelValue.value,
	(newVal) => {
		if (!newVal || (Array.isArray(newVal) && newVal.length === 0)) {
			if (props.presets.length > 0 && !isCustom.value) {
				selectPreset(props.presets[0])
			}
		} else if (!currentPresetMatch.value) {
			isCustom.value = true
		}
	},
	{ immediate: true, deep: true },
)

// Dropdown Options
const formControlOptions = computed(() => {
	const options = props.presets.map((p) => ({
		label: p.label,
		value: p.label,
		description: p.description?.(),
	}))
	options.push({ label: __('Custom'), value: 'Custom', description: '' })
	return options
})

const selectedFormControlValue = computed({
	get: () => {
		if (isCustom.value) return 'Custom'
		return currentPresetMatch.value ? currentPresetMatch.value.label : 'Custom'
	},
	set: (selectedLabel) => {
		if (selectedLabel === 'Custom') {
			isCustom.value = true
		} else {
			const preset = props.presets.find((p) => p.label === selectedLabel)
			if (preset) selectPreset(preset)
		}
	},
})

function onOptionChange(val: string | { value?: string } | null | undefined) {
	const selectedLabel = typeof val === 'string' ? val : val?.value
	if (!selectedLabel) return
	selectedFormControlValue.value = selectedLabel
}
</script>

<template>
	<Autocomplete
		class="w-full"
		:modelValue="selectedFormControlValue"
		@update:modelValue="onOptionChange"
		:options="formControlOptions"
		:hide-search="true"
	/>
	<div class="mt-2 w-full">
		<slot></slot>
	</div>
</template>
