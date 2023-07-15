<script setup lang="jsx">
import UsePopover from '@/components/UsePopover.vue'
import { useDataSource } from '@/datasource/useDataSource'
import useDataSources from '@/datasource/useDataSources'
import { whenever } from '@vueuse/core'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: Object })
const table = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const selectedDataSource = ref(null)
const sources = useDataSources()
sources.reload()
const sourceOptions = computed(() =>
	sources.list.map((source) => ({
		label: source.title,
		value: source.name,
		description: source.name,
	}))
)

const tableOptions = ref([])
whenever(selectedDataSource, async (newVal, oldVal) => {
	if (newVal == oldVal) return
	const dataSource = useDataSource(selectedDataSource.value)
	await dataSource.fetch_tables()

	tableOptions.value = dataSource.tables
		.filter((t) => !t.hidden)
		// remove duplicates
		.filter((sourceTable, index, self) => {
			return (
				self.findIndex((t) => {
					return t.table === sourceTable.table
				}) === index
			)
		})
		.map((sourceTable) => {
			return {
				table: sourceTable.table,
				value: sourceTable.table,
				label: sourceTable.label,
				description: sourceTable.table,
				data_source: dataSource.doc.name,
			}
		})
})

const trigger = ref(null)
const submenu = ref(null)

const dataSourcePopover = ref(null)
const datasourceSearchTerm = ref('')
const filteredSourceOptions = computed(() => {
	if (!datasourceSearchTerm.value) return sourceOptions.value
	if (!sourceOptions.value) return []
	return sourceOptions.value
		.filter((source) =>
			source.label.toLowerCase().includes(datasourceSearchTerm.value.toLowerCase())
		)
		.slice(0, 25)
})

const tablePopover = ref(null)
const tableSearchTerm = ref('')
const filteredTableOptions = computed(() => {
	if (!tableSearchTerm.value) return tableOptions.value
	if (!tableOptions.value) return []
	return tableOptions.value
		.filter((option) =>
			option.label.toLowerCase().includes(tableSearchTerm.value.toLowerCase())
		)
		.slice(0, 25)
})
function handleTableSelect(selectedTable) {
	selectedDataSource.value = null
	table.value = selectedTable
	dataSourcePopover.value.close()
	tablePopover.value.forEach((popover) => popover.close())
}
</script>

<template>
	<div>
		<div
			ref="trigger"
			class="flex h-7 w-full cursor-pointer items-center overflow-hidden text-ellipsis !whitespace-nowrap px-2.5 leading-7 outline-none ring-0 transition-all focus:outline-none"
			:class="table?.label ? '' : 'text-gray-500'"
		>
			<span> {{ table?.label || 'Pick starting data' }} </span>
		</div>
		<UsePopover ref="dataSourcePopover" v-if="trigger" :targetElement="trigger">
			<div class="w-[12rem] rounded border bg-white text-base shadow transition-[width]">
				<div class="flex items-center rounded-t-md border-b bg-white px-2">
					<FeatherIcon name="search" class="h-4 w-4 text-gray-600" />
					<input
						v-model="datasourceSearchTerm"
						class="flex w-full items-center bg-white p-2 text-sm focus:outline-none"
						placeholder="Search data source..."
					/>
				</div>
				<div class="max-h-48 overflow-y-auto text-sm">
					<p
						v-if="sourceOptions?.length === 0 || filteredSourceOptions?.length === 0"
						class="p-2 text-center text-gray-600"
					>
						No data sources found
					</p>
					<div
						v-else
						v-for="(source, index) in filteredSourceOptions"
						:key="source.value"
					>
						<div
							ref="submenu"
							class="flex cursor-pointer items-center justify-between p-2 transition-all hover:bg-gray-100"
							:class="selectedDataSource === source.value ? 'bg-gray-100' : ''"
							@click="selectedDataSource = source.value"
						>
							<span>{{ source.label }}</span>
							<FeatherIcon name="chevron-right" class="h-4 w-4" />
						</div>
						<UsePopover
							ref="tablePopover"
							v-if="submenu && submenu[index]"
							:targetElement="submenu[index]"
							placement="right-start"
						>
							<div
								class="-ml-3 w-[12rem] rounded border bg-white text-base shadow transition-[width]"
							>
								<div class="flex items-center rounded-t-md border-b bg-white px-2">
									<FeatherIcon name="search" class="h-4 w-4 text-gray-600" />
									<input
										v-model="tableSearchTerm"
										class="flex w-full items-center bg-white p-2 text-sm focus:outline-none"
										placeholder="Search table..."
									/>
								</div>
								<div class="max-h-48 overflow-y-auto text-sm">
									<p
										v-if="
											tableOptions?.length === 0 ||
											filteredTableOptions?.length === 0
										"
										class="p-2 text-center text-gray-600"
									>
										No tables found
									</p>
									<div
										v-for="t in filteredTableOptions"
										class="flex cursor-pointer items-center space-x-2 p-2 transition-all hover:bg-gray-100"
										:class="table?.value === t.value ? 'bg-gray-100' : ''"
										:key="t.value"
										@click="handleTableSelect(t)"
									>
										<!-- <FeatherIcon
											name="check"
											class="h-4 w-4 transition-opacity"
											:class="
												table?.value === t.value
													? 'opacity-100'
													: 'opacity-0'
											"
										/> -->
										<span>{{ t.label }}</span>
									</div>
								</div>
							</div>
						</UsePopover>
					</div>
				</div>
			</div>
		</UsePopover>
	</div>
</template>
