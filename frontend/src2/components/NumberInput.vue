<script setup lang="ts">
// A number box, writing a number.
//
// `FormControl type="number"` hands back a string, and a cleared box hands back
// an empty string. A config slot that declares a number then holds text, and
// `''` is not absent to `??`, so clearing an axis floor pins it at nothing
// instead of releasing it to the data's own extent. Every number a config form
// writes goes through this box, and `asNumber` is its one conversion.
import { FormControl } from 'frappe-ui'
import { asNumber } from '../helpers/typed_input'

const model = defineModel<number | undefined>()
</script>

<template>
	<FormControl
		type="number"
		autocomplete="off"
		v-bind="$attrs"
		:model-value="model"
		@update:model-value="model = asNumber($event)"
	/>
</template>
