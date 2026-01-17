<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ColumnOption, GroupedColumnOption } from '../../types/query.types'
import { column } from '../helpers'
import FormatRule from './FormatRule.vue'
import { FormatGroupArgs, FormattingMode } from './formatting_utils'

const props = defineProps<{
	initialRule?: FormattingMode | null
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()

const emit = defineEmits<{
	close: []
	select: [formatGroup: FormatGroupArgs]
}>()

const current = reactive<FormattingMode>(
	props.initialRule
		? ({ ...props.initialRule } as FormattingMode)
		: ({
				mode: 'cell_rules',
				column: column(''),
				operator: '=',
				color: 'red',
				value: 0,
		  } as any),
)

const selectedFormatMode = ref<'cell_rules' | 'color_scale'>(
	current.mode === 'color_scale' ? 'color_scale' : 'cell_rules',
)

function applyFormatting() {
	const group: FormatGroupArgs = { formats: [current], columns: [current.column] }
	emit('select', group)
}

const hasChanged = computed(() => {
	if (!props.initialRule) return true
	return JSON.stringify(props.initialRule) !== JSON.stringify(current)
})
</script>

<template>
	<div class="min-w-[20rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-2xl font-semibold leading-6 text-gray-900">Formatting Rule</h3>
			<Button variant="ghost" @click="() => emit('close')" icon="x" size="md"> </Button>
		</div>

		<div class="flex flex-col gap-3">
			<FormControl
				type="select"
				v-model="selectedFormatMode"
				label="Format Type"
				:options="[
					{ label: 'Highlight Cell', value: 'cell_rules' },
					{ label: 'Color Scale', value: 'color_scale' },
				]"
			>
			</FormControl>
			<FormatRule
				:modelValue="current"
				:columnOptions="props.columnOptions"
				:formatMode="selectedFormatMode"
				@update:modelValue="(val: any) => Object.assign(current, val)"
			/>
		</div>
		<div class="mt-6 flex items-center justify-end gap-2">
			<Button
				label="Apply"
				variant="solid"
				:disabled="!hasChanged"
				@click="applyFormatting"
			/>
		</div>
	</div>
</template>
