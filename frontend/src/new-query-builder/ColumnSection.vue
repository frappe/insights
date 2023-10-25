<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { AlignCenter, Calendar, CalendarClock, CaseUpper, Hash, X } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'

const typeToIcon = {
	String: CaseUpper,
	Text: AlignCenter,
	Date: Calendar,
	Datetime: CalendarClock,
	Integer: Hash,
	Decimal: Hash,
}

const query = inject('query')
const builder = inject('builder')

const columns = computed(() => builder.query.columns)
const columnRefs = ref(null)
const activeColumnIdx = ref(null)

function updateColumns(selectedOptions) {
	const addedColumns = selectedOptions.filter(
		(o) => !columns.value.find((c) => c.column === o.column && c.table === o.table)
	)
	builder.addColumns(addedColumns)
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<p class="font-medium">Summarize</p>
			<Autocomplete
				v-model="columns"
				:multiple="true"
				:options="query.columnOptions"
				bodyClasses="!w-[16rem]"
				@update:modelValue="updateColumns"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
				<template #footer>
					<Button class="w-full" variant="ghost" iconLeft="plus">
						Custom Expression
					</Button>
				</template>
			</Autocomplete>
		</div>
		<div class="space-y-2">
			<div
				ref="columnRefs"
				v-for="(column, idx) in columns"
				:key="column.id"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 text-sm hover:shadow"
				@click="activeColumnIdx = columns.indexOf(column)"
			>
				<div class="flex items-center space-x-2">
					<component :is="typeToIcon[column.type]" class="h-4 w-4 text-gray-600" />
					<div>{{ column.label }}</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click="builder.removeColumns([column])"
					/>
				</div>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="columnRefs?.[activeColumnIdx]"
		:show="activeColumnIdx !== null"
		@update:show="activeColumnIdx = null"
		:target-element="columnRefs[activeColumnIdx]"
	>
		<!-- Column Selector Popover -->
		<!-- A Column can be  -->
		<div class="w-full"></div>
	</UsePopover>
</template>
