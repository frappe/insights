<script setup lang="ts">
import { ref } from 'vue'
import { Dialog } from 'frappe-ui'
import { ColumnOption, GroupedColumnOption } from '../../types/query.types'
import { FormatGroupArgs } from './formatting_utils';
import FormattingSelector from './FormattingSelector.vue';

const props = defineProps<{
	formatGroup?: FormatGroupArgs,
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()

const emit = defineEmits({ select: (args: FormatGroupArgs) => true })
const showDialog = defineModel()

const formatGroup = ref<FormatGroupArgs>(props.formatGroup || { formats: [], columns: [] })

function onSelectFormat(updatedFormatGroup: FormatGroupArgs) {
	emit('select', updatedFormatGroup)
	showDialog.value = false
}
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: 'md' }">
		<template #body>
			<FormattingSelector
				v-model="formatGroup"
				:column-options="props.columnOptions"
				@select="onSelectFormat"
				@close="showDialog = false"
			/>
		</template>
	</Dialog>
</template>
