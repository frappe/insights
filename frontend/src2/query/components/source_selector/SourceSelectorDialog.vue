<script setup lang="tsx">
import { DatabaseIcon, Table2Icon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import TabbedSidebarLayout, { Tab, TabGroup } from '../../../components/TabbedSidebarLayout.vue'
import useDataSourceStore from '../../../data_source/data_source'
import { wheneverChanges } from '../../../helpers'
import { QueryTableArgs, SourceArgs, TableArgs } from '../../../types/query.types'
import { Workbook, workbookKey } from '../../../workbook/workbook'
import { query_table, table } from '../../helpers'
import DataSourceTableList from './DataSourceTableList.vue'
import WorkbookQueryList from './WorkbookQueryList.vue'

const emit = defineEmits({ select: (source: SourceArgs) => true })
const props = defineProps<{ source?: SourceArgs }>()
const showDialog = defineModel()

const selectedTable = ref<TableArgs>(
	props.source && props.source.table.type == 'table'
		? { ...props.source.table }
		: {
				type: 'table',
				data_source: '',
				table_name: '',
		  }
)

const dataSourceStore = useDataSourceStore()
const tabGroups = ref<TabGroup[]>([
	{
		groupLabel: 'Data Sources',
		tabs: [],
	},
])
const activeTab = ref<Tab | undefined>()
wheneverChanges(
	() => activeTab.value?.label,
	() => {
		selectedTable.value = {
			type: 'table',
			data_source: '',
			table_name: '',
		}
		selectedQuery.value = {
			type: 'query',
			workbook: '',
			query_name: '',
		}
	}
)

dataSourceStore.getSources().then(() => {
	tabGroups.value[0].tabs = dataSourceStore.sources
		.map((source) => ({
			label: source.title,
			icon: DatabaseIcon,
			component: () => (
				<DataSourceTableList
					v-model:selectedTable={selectedTable.value}
					data_source={source.name}
				/>
			),
		}))
		.sort((a, b) => a.label.localeCompare(b.label))

	activeTab.value = tabGroups.value[0].tabs[0]
	if (props.source && props.source.table.type == 'table') {
		const source_data_source = props.source.table.data_source
		const tab = tabGroups.value[0].tabs.find((tab) => tab.label == source_data_source)
		if (tab) activeTab.value = tab
	}
})

const selectedQuery = ref<QueryTableArgs>(
	props.source && props.source.table.type == 'query'
		? { ...props.source.table }
		: {
				type: 'query',
				workbook: '',
				query_name: '',
		  }
)
const workbook = inject<Workbook>(workbookKey)!
if (workbook.doc.queries.length > 1) {
	tabGroups.value.push({
		groupLabel: 'Workbook',
		tabs: [
			{
				label: 'Queries',
				icon: Table2Icon,
				component: () => <WorkbookQueryList v-model:selectedQuery={selectedQuery.value} />,
			},
		],
	})
	if (props.source && props.source.table.type == 'query') {
		activeTab.value = tabGroups.value[1].tabs[0]
	}
}

const confirmDisabled = computed(() => {
	return !selectedTable.value.table_name && !selectedQuery.value.query_name
})

function onConfirm() {
	if (confirmDisabled.value) return
	emit(
		'select',
		selectedQuery.value.query_name
			? {
					table: query_table(selectedQuery.value),
			  }
			: {
					table: table(selectedTable.value),
			  }
	)
	showDialog.value = false
}
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: '4xl' }">
		<template #body>
			<div class="relative flex pb-10" :style="{ height: 'calc(100vh - 12rem)' }">
				<TabbedSidebarLayout
					title="Pick Starting Data"
					:tabs="tabGroups"
					v-model:activeTab="activeTab"
				/>
				<div class="absolute bottom-3 right-3 flex gap-2">
					<Button @click="showDialog = false"> Close </Button>
					<Button variant="solid" :disabled="confirmDisabled" @click="onConfirm">
						Confirm
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
