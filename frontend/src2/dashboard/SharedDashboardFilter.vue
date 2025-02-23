<script setup lang="ts">
import { reactive } from 'vue'
import { copy } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { createToast } from '../helpers/toasts'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { ColumnDataType } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'

const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
if (!filter.links) {
	filter.links = {}
}

const FILTER_TYPES = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}
</script>

<template>
	<div class="h-8 w-full">
		<Button
			class="flex h-full w-full !justify-start"
			:label="filter.filter_name || 'Filter'"
			variant="outline"
			@click="
				() => {
					createToast({
						variant: 'warning',
						title: 'Not supported',
						message: 'Filtering charts is not supported yet in shared dashboards.',
					})
				}
			"
		>
			<template #prefix>
				<DataTypeIcon
					v-if="filter.filter_type"
					:column-type="(FILTER_TYPES[filter.filter_type][0] as ColumnDataType)"
					class="h-4 w-4 flex-shrink-0"
					stroke-width="1.5"
				/>
			</template>
		</Button>
	</div>
</template>
