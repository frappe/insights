<script setup lang="ts">
import { computed } from 'vue'
import { ColumnOption, FilterGroupArgs, GroupedColumnOption } from '../../types/query.types'
import { __ } from '../../translation'
import FiltersSelector from './FiltersSelector.vue'

const props = defineProps<{
	filterGroup?: FilterGroupArgs
	columnOptions: ColumnOption[] | GroupedColumnOption[]
	disableLogicalOperator?: boolean
	disableExpressions?: boolean
}>()
const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
</script>

<template>
	<Dialog
		v-model:open="showDialog"
		:dismissible="false"
		:title="__('Filter')"
		size="2xl"
		@close="showDialog = false"
	>
		<template #default>
			<FiltersSelector
				:filterGroup="props.filterGroup"
				:columnOptions="props.columnOptions"
				:disableLogicalOperator="props.disableLogicalOperator"
				:disableExpressions="props.disableExpressions"
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
