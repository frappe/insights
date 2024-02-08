<script setup>
import useDataSource from '@/datasource/useDataSource'
import useDataSourceTable from '@/datasource/useDataSourceTable'
import useDataSourceStore from '@/stores/dataSourceStore'
import { computed, inject, ref, watch } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({ show: Boolean })

const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

const dataSources = computed(() =>
	useDataSourceStore().list.map((d) => {
		return {
			title: d.title,
			name: d.name,
		}
	})
)
const currentTables = ref([])
const currentColumns = ref([])

const query = inject('query')
const currentDataSource = ref(null)
watch(
	() => query?.doc?.data_source,
	(value) => {
		if (!value) return
		currentDataSource.value = { name: value }
	},
	{ immediate: true }
)
const currentTable = ref(null)

watch(
	currentDataSource,
	() => {
		if (!currentDataSource.value) return
		currentTables.value = []
		currentColumns.value = []
		const dataSource = useDataSource(currentDataSource.value.name)
		dataSource.fetchTables().then((tables) => {
			currentTables.value = tables.map((t) => {
				return {
					label: t.label,
					table: t.table,
					name: t.name,
				}
			})
		})
	},
	{ immediate: true }
)

const fetchingColumns = ref(false)
watch(
	currentTable,
	async () => {
		if (!currentTable.value) return
		currentColumns.value = []
		fetchingColumns.value = true
		const table = await useDataSourceTable({ name: currentTable.value.name })
		fetchingColumns.value = false
		currentColumns.value = table.columns.map((c) => {
			return {
				label: c.label,
				column: c.column,
				type: c.type,
			}
		})
	},
	{ immediate: true }
)

function toggleDataSource(dataSource) {
	if (currentDataSource.value?.name == dataSource.name) {
		currentDataSource.value = null
	} else {
		currentDataSource.value = dataSource
	}
}
function toggleTable(table) {
	if (currentTable.value?.name == table.name) {
		currentTable.value = null
	} else {
		currentTable.value = table
	}
}
</script>
<template>
	<Dialog v-model="show" :options="{ title: 'Browse Data Sources' }">
		<template #body-content>
			<div
				class="-ml-2 h-[32rem] w-full overflow-y-auto overflow-x-hidden overflow-y-hidden pl-2"
			>
				<div class="flex flex-col gap-1">
					<div
						v-for="dataSource in dataSources"
						:key="dataSource.name"
						class="flex cursor-pointer flex-col space-x-4"
					>
						<div
							class="-ml-1 flex flex-1 cursor-pointer items-center gap-2 rounded py-1 pl-1 transition-colors hover:bg-gray-100"
							:class="
								currentDataSource?.name == dataSource.name && !currentTable
									? 'bg-gray-100'
									: ''
							"
							@click="toggleDataSource(dataSource)"
						>
							<FeatherIcon
								:name="
									currentDataSource?.name == dataSource.name ? 'minus' : 'plus'
								"
								class="h-4 w-4"
							/>
							<div class="flex items-center gap-2">
								<FeatherIcon name="database" class="h-4 w-4 text-gray-600" />
								<p class="font-medium leading-6 text-gray-900">
									{{ dataSource.title }}
								</p>
							</div>
						</div>
						<div
							v-if="currentDataSource?.name == dataSource.name"
							class="mt-1 flex flex-col gap-1"
						>
							<div v-for="table in currentTables" :key="table.name" class="pl-2">
								<div
									class="-ml-1 flex flex-1 cursor-pointer items-center gap-2 rounded py-1 pl-1 transition-colors hover:bg-gray-100"
									:class="currentTable?.name == table.name ? 'bg-gray-100' : ''"
									@click="toggleTable(table)"
								>
									<FeatherIcon
										:name="currentTable?.name == table.name ? 'minus' : 'plus'"
										class="h-4 w-4"
									/>
									<div class="flex items-center gap-2">
										<FeatherIcon name="folder" class="h-4 w-4 text-gray-600" />
										<p class="font-medium leading-6 text-gray-900">
											{{ table.label }}
										</p>
									</div>
								</div>
								<div
									v-if="currentTable?.name == table.name"
									class="mt-1 ml-4 mb-1 flex items-center justify-center"
								>
									<LoadingIndicator
										v-if="fetchingColumns"
										class="w-6 text-gray-600"
									/>
									<div v-else class="w-full space-y-2">
										<div v-for="column in currentColumns" :key="column.column">
											<div class="flex items-center space-x-2 pl-2">
												<FeatherIcon
													name="type"
													class="h-4 w-4 text-gray-600"
												/>
												<p class="font-medium leading-6 text-gray-900">
													{{ column.label }}
												</p>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
