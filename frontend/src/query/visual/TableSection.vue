<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import UsePopover from '@/components/UsePopover.vue'
import useDataSource from '@/datasource/useDataSource'
import { whenever } from '@vueuse/core'
import { ExternalLink, GanttChartSquare, Sheet, Table2, X } from 'lucide-vue-next'
import { computed, inject, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import SectionHeader from './SectionHeader.vue'
import TableJoinEditor from './TableJoinEditor.vue'

const assistedQuery = inject('assistedQuery')

let dataSource = reactive({})
whenever(
	() => assistedQuery.data_source,
	(newVal, oldVal) => {
		if (!newVal) return
		if (newVal == oldVal) return
		dataSource = useDataSource(assistedQuery.data_source)
		dataSource.fetchTables()
	},
	{ immediate: true }
)

const joins = computed(() => assistedQuery.joins)
const joinRefs = ref([])
const activeJoinIdx = ref(null)

function onSaveJoin(newJoin) {
	assistedQuery.updateJoinAt(activeJoinIdx.value, newJoin)
	activeJoinIdx.value = null
}
function onRemoveJoin() {
	assistedQuery.removeJoinAt(activeJoinIdx.value)
	activeJoinIdx.value = null
}

const router = useRouter()
function onTableLinkClick(table) {
	const route = table.startsWith('QRY-')
		? router.resolve({ name: 'Query', params: { name: table } })
		: router.resolve({ name: 'DataSource', params: { name: assistedQuery.data_source } })
	window.open(route.href, '_blank')
}
</script>

<template>
	<div :key="assistedQuery.data_source" class="space-y-2">
		<SectionHeader
			:icon="Sheet"
			title="Tables"
			info="Select the tables you want to extract data from."
		>
			<Autocomplete
				bodyClasses="w-[18rem]"
				:options="dataSource.groupedTableOptions"
				@update:modelValue="$event && assistedQuery.addTable($event)"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
			</Autocomplete>
		</SectionHeader>
		<div class="space-y-2">
			<div
				v-if="assistedQuery.table.table"
				class="group relative flex h-8 cursor-pointer items-center justify-between overflow-hidden rounded border border-gray-300 bg-white px-2 pl-2.5 hover:shadow"
			>
				<div class="absolute left-0 h-full w-1 flex-shrink-0 bg-orange-500"></div>
				<div class="flex flex-1 items-center gap-1 overflow-hidden">
					<component
						:is="
							assistedQuery.table.table.startsWith('QRY-') ? GanttChartSquare : Table2
						"
						class="h-4 w-4 flex-shrink-0 text-gray-600"
					/>
					<div class="flex flex-1 items-center gap-1 overflow-hidden">
						<span class="truncate">{{ assistedQuery.table.label }}</span>
						<ExternalLink
							class="h-3 w-3 text-gray-600 opacity-0 transition-all hover:text-gray-800 group-hover:opacity-100"
							@click.prevent.stop="onTableLinkClick(assistedQuery.table.table)"
						/>
					</div>
				</div>
				<div class="ml-2 flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click="assistedQuery.resetMainTable()"
					/>
				</div>
			</div>
			<div
				ref="joinRefs"
				v-for="(join, idx) in joins"
				:key="join.right_table.table"
				class="group relative flex h-8 cursor-pointer items-center justify-between overflow-hidden rounded border border-gray-300 bg-white px-2 pl-2.5 hover:shadow"
				:class="
					idx === activeJoinIdx
						? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400'
						: ''
				"
				@click="activeJoinIdx = idx"
			>
				<div class="absolute left-0 h-full w-1 flex-shrink-0 bg-orange-500"></div>
				<div class="flex flex-1 items-center gap-1">
					<component
						:is="join.right_table.table.startsWith('QRY-') ? GanttChartSquare : Table2"
						class="h-4 w-4 text-gray-600"
					/>
					<span class="truncate">{{ join.right_table.label }}</span>
					<ExternalLink
						class="h-3 w-3 text-gray-600 opacity-0 transition-all hover:text-gray-800 group-hover:opacity-100"
						@click.prevent.stop="onTableLinkClick(join.right_table.table)"
					/>
				</div>
				<JoinLeftIcon v-if="join.join_type.value == 'left'" class="text-gray-600" />
				<JoinRightIcon v-if="join.join_type.value == 'right'" class="text-gray-600" />
				<JoinInnerIcon v-if="join.join_type.value == 'inner'" class="text-gray-600" />
				<JoinFullIcon v-if="join.join_type.value == 'full'" class="text-gray-600" />
			</div>
		</div>
	</div>

	<UsePopover
		v-if="joinRefs?.[activeJoinIdx]"
		:key="activeJoinIdx"
		:show="activeJoinIdx !== null"
		@update:show="activeJoinIdx = null"
		:target-element="joinRefs[activeJoinIdx]"
		placement="right-start"
	>
		<div class="min-w-[24rem] rounded bg-white text-base shadow-2xl">
			<TableJoinEditor
				:join="joins[activeJoinIdx]"
				@save="onSaveJoin($event)"
				@discard="activeJoinIdx = null"
				@remove="onRemoveJoin"
			/>
		</div>
	</UsePopover>
</template>
