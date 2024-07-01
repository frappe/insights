<script setup lang="ts">
import { computed, watch } from 'vue'
import { FilterOperator, QueryResultColumn } from '../../types/query.types'

const props = defineProps<{ column: QueryResultColumn }>()
const filter = defineModel<{ operator: FilterOperator; value: any }>({
	type: Object,
	default: () => ({ operator: '=', value: [0, 0] }),
})

// const query = inject('query') as Query
// onMounted(() => {
// 	if (!filter.value.value?.[0] && !filter.value.value?.[1]) {
// 		query.getMinAndMax(props.column.name).then((minMax: number[]) => {
// 			console.log(minMax)
// 			if (typeof minMax[0] === 'number' && typeof minMax[1] === 'number') {
// 				filter.value.value = minMax
// 			}
// 		})
// 	}
// })

watch(
	() => filter.value.value,
	() => {
		// set operator based on value
		if (filter.value.value[0] === filter.value.value[1]) {
			filter.value.operator = '='
		} else if (filter.value.value[0] && !filter.value.value[1]) {
			filter.value.operator = '>='
		} else if (!filter.value.value[0] && filter.value.value[1]) {
			filter.value.operator = '<='
		} else if (filter.value.value[0] && filter.value.value[1]) {
			filter.value.operator = 'between'
		}
	},
	{ deep: true }
)

const numberFilterDescription = computed(() => {
	if (!filter.value.value[0] && !filter.value.value[1]) {
		return ''
	}
	if (filter.value.value[0] === filter.value.value[1]) {
		return `${props.column.name} is ${filter.value.value[0]}`
	}
	if (filter.value.value[0] && !filter.value.value[1]) {
		return `${props.column.name} is ${filter.value.value[0]} or greater`
	}
	if (!filter.value.value[0] && filter.value.value[1]) {
		return `${props.column.name} is ${filter.value.value[1]} or less`
	}
	return `${props.column.name} is between ${filter.value.value[0]} and ${filter.value.value[1]}`
})
</script>

<template>
	<div>
		<div class="flex gap-2">
			<FormControl type="number" placeholder="Min" label="Min" v-model="filter.value[0]" />
			<FormControl type="number" placeholder="Max" label="Max" v-model="filter.value[1]" />
		</div>
		<p class="mt-1 text-xs leading-4 text-gray-600">
			{{ numberFilterDescription }}
		</p>
	</div>
</template>
