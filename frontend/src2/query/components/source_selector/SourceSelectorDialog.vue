<script setup lang="tsx">
import { DatabaseIcon, Table2Icon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import useDataSourceStore from '../../../data_source/data_source'
import { wheneverChanges } from '../../../helpers'
import { SourceArgs, TableArgs } from '../../../types/query.types'
import { Workbook, workbookKey } from '../../../workbook/workbook'
import { table } from '../../helpers'
import DataSourceTableList from './DataSourceTableList.vue'
import TabbedSidebarLayout, { Tab, TabGroup } from './TabbedSidebarLayout.vue'
import WorkbookQueryList from './WorkbookQueryList.vue'

const emit = defineEmits({ select: (source: SourceArgs) => true })
const props = defineProps<{ source?: SourceArgs }>()
const showDialog = defineModel()

const selectedTable = ref<TableArgs>(
	props.source && 'table' in props.source
		? { ...props.source.table }
		: {
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
wheneverChanges(activeTab, () => {
	selectedTable.value = {
		data_source: '',
		table_name: '',
	}
	selectedQuery.value = ''
})

dataSourceStore.getSources().then(() => {
	tabGroups.value[0].tabs = dataSourceStore.sources.map((source) => ({
		label: source.name,
		icon: DatabaseIcon,
		component: () => (
			<DataSourceTableList
				v-model:selectedTable={selectedTable.value}
				data_source={source.name}
			/>
		),
	}))
	activeTab.value = tabGroups.value[0].tabs[0]
})

const selectedQuery = ref(props.source && 'query' in props.source ? props.source.query : '')
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
}

const confirmDisabled = computed(() => {
	return !selectedTable.value?.table_name && !selectedQuery.value
})

function onConfirm() {
	if (confirmDisabled.value) return
	emit(
		'select',
		selectedQuery.value
			? {
					query: selectedQuery.value,
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
			<div class="relative flex" :style="{ height: 'calc(100vh - 12rem)' }">
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
