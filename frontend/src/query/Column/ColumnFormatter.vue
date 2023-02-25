<template>
	<div v-if="!supportsFormatting" class="px-12 text-center text-sm font-light text-gray-600">
		<p class="mb-2">The app doesn't support formatting for this column type just yet</p>
		<a href="https://github.com/frappe/insights/issues/new" class="text-blue-400 underline">
			Do you want to raise a feature request?
		</a>
	</div>
	<div v-else class="flex flex-col space-y-3">
		<div v-if="showNumberFormatOptions" class="space-y-3 text-sm text-gray-600">
			<div class="space-y-1">
				<div class="font-light">Prefix</div>
				<Input type="text" v-model="format.prefix" placeholder="Enter a prefix..." />
			</div>
			<div class="space-y-1">
				<div class="font-light">Suffix</div>
				<Input type="text" v-model="format.suffix" placeholder="Enter a suffix..." />
			</div>
		</div>
		<div class="flex justify-end space-x-2">
			<Button @click="clearFormattingOptions" appearance="white" :disabled="false">
				Clear
			</Button>
			<Button @click="saveFormattingOptions" appearance="primary" :disabled="false">
				Save
			</Button>
		</div>
	</div>
</template>

<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import { reactive, ref, unref } from 'vue'

const emit = defineEmits(['save'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		required: true,
	},
})

const supportsFormatting = ref(['Integer', 'Decimal'].includes(props.column.type))
const columnFormat = props.column.format_option || {}
const format = reactive({
	prefix: columnFormat.prefix || '',
	suffix: columnFormat.suffix || '',
})

const showNumberFormatOptions = ref(['Integer', 'Decimal'].includes(props.column.type))
const saveFormattingOptions = () => {
	const updatedColumn = unref(props.column)
	updatedColumn.format_option = null
	if (showNumberFormatOptions.value) {
		updatedColumn.format_option = {
			prefix: format.prefix,
			suffix: format.suffix,
		}
	}
	emit('save', updatedColumn)
}

const clearFormattingOptions = () => {
	const updatedColumn = unref(props.column)
	updatedColumn.format_option = null
	emit('save', updatedColumn)
}
</script>
