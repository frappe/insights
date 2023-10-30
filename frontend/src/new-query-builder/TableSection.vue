<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import UsePopover from '@/components/UsePopover.vue'
import useDataSource from '@/datasource/useDataSource'
import { whenever } from '@vueuse/core'
import { computed, inject, ref } from 'vue'
import TableJoinEditor from './TableJoinEditor.vue'
import { X } from 'lucide-vue-next'

const builder = inject('builder')

let dataSource = useDataSource(builder.data_source)
dataSource.fetchTables()
whenever(
	() => builder.data_source,
	(newVal, oldVal) => {
		if (newVal == oldVal) return
		dataSource = useDataSource(builder.data_source)
		dataSource.fetchTables()
	}
)

const joins = computed(() => builder.query.joins)
const joinRefs = ref([])
const activeJoinIdx = ref(null)

function onRemoveJoin() {
	builder.query.joins.splice(activeJoinIdx, 1)
	activeJoinIdx.value = null
}
function onSaveJoin(newJoin) {
	builder.query.joins.splice(activeJoinIdx, 1, newJoin)
	activeJoinIdx.value = null
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<p class="font-medium">Data</p>
			<Autocomplete
				:options="dataSource.groupedTableOptions"
				@update:modelValue="builder.addTable($event)"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
			</Autocomplete>
		</div>
		<div class="space-y-2">
			<div
				v-if="builder.query.table.table"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
			>
				<div class="flex items-center space-x-2">
					<div>{{ builder.query.table.label }}</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click="builder.resetMainTable()"
					/>
				</div>
			</div>
			<div
				ref="joinRefs"
				v-for="(join, idx) in joins"
				:key="join.right_table.table"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				@click="activeJoinIdx = idx"
			>
				<div>{{ join.right_table.label }}</div>
				<JoinLeftIcon class="text-gray-600" />
			</div>
		</div>
	</div>

	<UsePopover
		v-if="joinRefs?.[activeJoinIdx]"
		:key="activeJoinIdx"
		:show="activeJoinIdx !== null"
		@update:show="activeJoinIdx = null"
		:target-element="joinRefs[activeJoinIdx]"
	>
		<div class="w-[28rem] rounded bg-white text-base shadow-md">
			<TableJoinEditor
				:join="joins[activeJoinIdx]"
				@remove="onRemoveJoin()"
				@save="onSaveJoin($event)"
			/>
		</div>
	</UsePopover>
</template>
