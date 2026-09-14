<script setup lang="ts">
// A number box, writing a number.
//
// `FormControl type="number"` hands back a string, and a cleared box hands back
// an empty string. A config slot that declares a number then carries text, and
// `''` is not absent to `??`, so clearing an axis floor pins it at nothing
// instead of releasing it to the data's own extent. The conversion belongs to
// the field, once, rather than to each of its writers.
import { FormControl } from 'frappe-ui'

const model = defineModel<number | undefined>()

function write(value: any) {
	const number = Number(value)
	model.value =
		value === '' || value === null || value === undefined || !Number.isFinite(number)
			? undefined
			: number
}
</script>

<template>
	<FormControl
		type="number"
		autocomplete="off"
		v-bind="$attrs"
		:model-value="model"
		@update:model-value="write"
	/>
</template>
