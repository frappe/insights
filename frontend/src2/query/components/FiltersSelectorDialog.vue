<script setup lang="ts">
import { computed } from 'vue'
import { ColumnOption, FilterGroupArgs, GroupedColumnOption } from '../../types/query.types'
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
		v-model="showDialog"
		:disableOutsideClickToClose="true"
		:options="{ size: '2xl', title: 'Filter' }"
		@close="showDialog = false"
	>
		<template #body-content>
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
