<script setup lang="ts">
import { FIELDTYPES } from '@/utils'
import { ChevronRight, ListFilter } from 'lucide-vue-next'
import { computed, reactive } from 'vue'
import { QueryResultColumn } from '../useQuery'
import ColumnFilterTypeDate from './ColumnFilterTypeDate.vue'
import ColumnFilterTypeNumber from './ColumnFilterTypeNumber.vue'
import ColumnFilterTypeText from './ColumnFilterTypeText.vue'

const emit = defineEmits({
	filter: (operator: FilterOperator, value: FilterValue) => true,
})
const props = defineProps<{ column: QueryResultColumn }>()

const isText = computed(() => FIELDTYPES.TEXT.includes(props.column.type))
const isNumber = computed(() => FIELDTYPES.NUMBER.includes(props.column.type))
const isDate = computed(() => FIELDTYPES.DATE.includes(props.column.type))

const initialFilter = {
	operator: '=' as FilterOperator,
	value: [] as FilterValue,
}
const newFilter = reactive({ ...initialFilter })

const isValidFilter = computed(() => {
	if (!newFilter.operator) return false
	if (isText.value && newFilter.operator.includes('set')) return true

	if (!newFilter.value) return false
	if (isText.value && newFilter.operator.includes('contains')) return newFilter.value

	const value = newFilter.value as any[] // number & date value is always an array
	if (isNumber.value) return value[0] || value[1]
	if (isDate.value) return value[0] || value[1]
	if (isText.value && newFilter.operator.includes('=')) return value.length

	return false
})

function processFilter(operator: FilterOperator, value: FilterValue) {
	if (isNumber.value && Array.isArray(value)) {
		value = value.map((v) => (!isNaN(v) ? String(v) : v))
		if (operator === '=' && value[0] === value[1]) return ['=', Number(value[0])]
		if (operator === '>=' && value[0] && !value[1]) return ['>=', Number(value[0])]
		if (operator === '<=' && !value[0] && value[1]) return ['<=', Number(value[1])]
		if (operator === 'between' && value[0] && value[1])
			return ['between', Number(value[0]), Number(value[1])]
	}

	if (isText.value) {
		if (operator.includes('set')) return [operator, value]
		if (operator.includes('contains')) return [operator, value]
		if (operator.includes('=')) {
			return [operator === '!=' ? 'not_in' : 'in', value]
		}
	}

	if (isDate.value && Array.isArray(value)) {
		if (operator === '=' && value[0] === value[1]) return ['=', value[0]]
		if (operator === '>=' && value[0] && !value[1]) return ['>=', value[0]]
		if (operator === '<=' && !value[0] && value[1]) return ['<=', value[1]]
		if (operator === 'within') return ['within', value]
		if (operator === 'between' && value[0] && value[1]) return ['between', [value[0], value[1]]]
	}
}

function addFilter() {
	const filter = processFilter(newFilter.operator, newFilter.value)
	if (!filter) {
		console.error(newFilter.operator, newFilter.value)
		throw new Error('Invalid filter')
	}
	emit('filter', filter[0], filter[1])
	Object.assign(newFilter, { ...initialFilter })
}
</script>

<template>
	<Popover placement="right-start">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				@click="togglePopover"
				class="w-full !justify-start"
				:class="{ ' !bg-gray-100': isOpen }"
			>
				<template #icon>
					<div class="flex h-7 w-full items-center gap-2 pl-2 pr-1.5 text-base">
						<ListFilter class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
						<div class="flex flex-1 items-center justify-between">
							<span class="truncate">Filter</span>
							<ChevronRight class="h-4 w-4" stroke-width="1.5" />
						</div>
					</div>
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<div v-if="isOpen" class="flex flex-col gap-2 p-2.5">
				<div class="flex items-center text-sm font-medium text-gray-600">
					Filter: {{ props.column.name }}
				</div>

				<ColumnFilterTypeNumber
					v-if="isNumber"
					class="w-[16rem]"
					:column="props.column"
					:model-value="newFilter"
					@update:model-value="Object.assign(newFilter, $event)"
				/>
				<ColumnFilterTypeText
					v-else-if="isText"
					class="w-[16rem]"
					:column="props.column"
					:model-value="newFilter"
					@update:model-value="Object.assign(newFilter, $event)"
				/>
				<ColumnFilterTypeDate
					v-else-if="isDate"
					:column="props.column"
					:model-value="(newFilter as any)"
					@update:model-value="Object.assign(newFilter, $event)"
				/>

				<div class="flex justify-end gap-1">
					<Button @click="togglePopover" icon="x"></Button>
					<Button
						variant="solid"
						icon="check"
						:disabled="!isValidFilter"
						@click=";[addFilter(), togglePopover()]"
					>
					</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
