<script setup lang="ts">
import { computed, inject } from 'vue'
import { FilterGroupArgs } from '../../types/query.types'
import { Query } from '../query'
import FiltersSelector from './FiltersSelector.vue'

const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
const query = inject('query') as Query

const columnOptions = computed(() =>
	query.result.columnOptions.map((c) => ({
		...c,
		query: query.doc.name,
	}))
)
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FiltersSelector
				:columnOptions="columnOptions"
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
