<script setup lang="ts">
import { reactive, watch } from 'vue'
import FilterControl from './FilterControl.vue'
import { isFilterApplied } from '../query/components/filter_utils'
import { __ } from '../translation'
import type { FilterType } from '../helpers/constants'
import type { FilterOperator, FilterValue } from '../types/query.types'
import { fetchFilterValues, ViewerDashboardItem, ViewerFilters } from './viewer'

type DraftState = { operator?: FilterOperator; value?: FilterValue }

// The one surface a pure viewer acts on. It is not a grid cell: filters sit in
// the page's header band, above the cards, and stay in reach while the grid
// scrolls under them. The band owns the spacing — this is a row inside it, not
// a surface that positions itself.
const props = defineProps<{
	dashboard: string
	items: ViewerDashboardItem[]
}>()

const filters = defineModel<ViewerFilters>({ required: true })

// what the controls edit. A control reports its operator and its value as two
// changes; collecting them here means one settled state per tick, and so one
// refetch of the cards a filter reaches.
const draft = reactive<Record<string, DraftState>>({})

props.items.forEach((item) => {
	const name = item.filter_name!
	const restored = filters.value[name]
	draft[name] = restored
		? { operator: restored.operator, value: restored.value }
		: // a filter with no default arrives as null, and the value pickers read an
		  // absent value as undefined
		  { operator: item.default_operator ?? undefined, value: item.default_value ?? undefined }
})

watch(
	draft,
	() => {
		const applied: ViewerFilters = {}
		props.items.forEach((item) => {
			const state = draft[item.filter_name!]
			if (isFilterApplied(item.filter_type as FilterType, state?.operator, state?.value)) {
				applied[item.filter_name!] = {
					operator: state.operator as FilterOperator,
					value: state.value as FilterValue,
				}
			}
		})
		filters.value = applied
	},
	{ deep: true, immediate: true },
)

function reset() {
	props.items.forEach((item) => {
		draft[item.filter_name!] = { operator: undefined, value: undefined }
	})
}

defineExpose({ reset })
</script>

<template>
	<div class="flex flex-wrap items-center gap-2">
		<FilterControl
			v-for="item in props.items"
			:key="item.filter_name"
			class="w-fit min-w-36 max-w-64"
			:filter-name="item.filter_name!"
			:filter-type="item.filter_type as FilterType"
			:icon="item.icon"
			:values-provider="
				(search: string) => fetchFilterValues(props.dashboard, item.filter_name!, search)
			"
			v-model:operator="draft[item.filter_name!].operator"
			v-model:value="draft[item.filter_name!].value"
		/>

		<Button
			v-if="Object.keys(filters).length"
			variant="ghost"
			:label="__('Reset')"
			@click="reset"
		/>
	</div>
</template>
