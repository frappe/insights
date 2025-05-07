<script setup lang="ts">
import { ColumnOption, GroupedColumnOption } from '../../types/query.types'
import { FormatGroupArgs } from './formatting_utils';
import FormattingSelector from './FormattingSelector.vue';

const props = defineProps<{
	formatGroup?: FormatGroupArgs,
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()
const emit = defineEmits({ select: (args: FormatGroupArgs) => true })
const showDialog = defineModel()
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FormattingSelector
				:formatGroup="props.formatGroup"
				:columnOptions="props.columnOptions"

				@close="showDialog = false"
				@select="
					(args) => {
						emit('select', args)
						showDialog = false
					}
				"
			/>
		</template>
	</Dialog>
</template>
