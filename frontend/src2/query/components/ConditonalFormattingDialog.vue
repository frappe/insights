<script setup lang="ts">
import { ref } from 'vue'
import { Dialog } from 'frappe-ui'
import { ColumnOption, GroupedColumnOption,  } from '../../types/query.types'
import { FormatGroupArgs, FormattingMode } from './formatting_utils';
import FormattingSelector from './FormattingSelector.vue';

const props = defineProps<{
  columnOptions: ColumnOption[] | GroupedColumnOption[] | [],
  initialRule?: FormattingMode | null,
  selectorKey?: string | number
}>()

const emit = defineEmits({ select: (args: FormatGroupArgs) => true })
const showDialog = defineModel()

function onSelectFormat(updatedFormatGroup: FormatGroupArgs) {
	emit('select', updatedFormatGroup)
	showDialog.value = false
}
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: 'md' }">
		<template #body>
			<FormattingSelector
				:key="props.selectorKey ?? 'new'"
				:initial-rule="props.initialRule ?? null"
				:column-options="props.columnOptions"
				@select="onSelectFormat"
				@close="showDialog = false"
			/>
		</template>
	</Dialog>
</template>
