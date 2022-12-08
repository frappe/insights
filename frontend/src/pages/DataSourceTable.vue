<template>
	<BasePage>
		<template #header>
			<div v-if="doc" class="flex flex-1 items-center space-x-4">
				<div class="flex items-start space-x-4">
					<h1 class="text-3xl font-medium text-gray-900">
						{{ doc.label }}
					</h1>
					<div class="flex h-8 items-center">
						<Badge :color="hidden ? 'yellow' : 'green'" class="h-fit">
							{{ hidden ? 'Disabled' : 'Enabled' }}
						</Badge>
					</div>
				</div>
				<div class="space-x-2">
					<Dropdown
						placement="left"
						:button="{
							icon: 'more-horizontal',
							appearance: 'minimal',
						}"
						:options="[
							{
								label: hidden ? 'Enable' : 'Disable',
								icon: hidden ? 'eye' : 'eye-off',
								handler: () => (hidden = !hidden),
							},
							{
								label: 'Sync Table',
								icon: 'refresh-cw',
								handler: () => dataSourceTable.sync(),
							},
							{
								label: 'Add Link',
								icon: 'link',
								handler: () => (addLinkDialog = true),
							},
						]"
					/>
				</div>
			</div>
		</template>
		<template #main>
			<div
				v-if="doc && doc.columns && dataSourceTable.rows?.data"
				class="flex h-full w-full flex-col pt-1"
			>
				<div class="flex h-6 space-x-1 text-sm font-light text-gray-600">
					{{ doc.columns.length }} Columns - {{ dataSourceTable.rows.length }} Rows
				</div>
				<div class="h-[calc(100%-1.5rem)] w-full">
					<Grid
						v-if="!dataSourceTable.syncing"
						:header="true"
						:rows="dataSourceTable.rows.data"
					>
						<template #header>
							<DataSourceTableColumnHeader
								:columns="doc.columns"
								@update-column-type="dataSourceTable.updateColumnType"
							/>
						</template>
					</Grid>
					<div
						v-else
						class="mt-2 flex h-full flex-col items-center justify-center rounded-md bg-gray-50"
					>
						<Spinner class="mb-2 w-8 text-gray-400" />
						<div class="text-lg text-gray-500">Syncing columns from database...</div>
					</div>
				</div>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Create a Link' }" v-model="addLinkDialog">
		<template #body-content>
			<div class="space-y-4">
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">Table</div>
					<Autocomplete
						v-model="newLink.table"
						:options="tableOptions"
						placeholder="Select a table..."
					/>
				</div>
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">
						Select a column from {{ doc.label }}
					</div>
					<Autocomplete
						v-model="newLink.primaryKey"
						:options="
							doc.columns.map((c) => ({
								label: `${c.label} (${c.type})`,
								value: c.column,
							}))
						"
					/>
				</div>
				<div v-if="newLink.table?.value">
					<div class="mb-2 block text-sm leading-4 text-gray-700">
						Select a column from {{ newLink.table.label }}
					</div>
					<Autocomplete v-model="newLink.foreignKey" :options="foreignKeyOptions" />
				</div>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				@click="createLink"
				:loading="creatingLink"
				:disabled="createLinkDisabled"
			>
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Grid from '@/components/Grid.vue'
import DataSourceTableColumnHeader from './DataSourceTableColumnHeader.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { useDataSourceTable } from '@/utils/datasource'
import { Dropdown, Badge, createResource, Spinner } from 'frappe-ui'
import { computed, ref, reactive, watch, inject } from 'vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
	table: {
		type: String,
		required: true,
	},
})

const addLinkDialog = ref(false)
const newLink = reactive({
	table: {},
	primaryKey: {},
	foreignKey: {},
})

const dataSourceTable = useDataSourceTable(props.table)
const doc = computed(() => {
	return dataSourceTable.doc
})
const hidden = computed({
	get() {
		return doc.value.hidden
	},
	set(value) {
		if (value !== doc.value.hidden) {
			dataSourceTable.updateVisibility(value)
		}
	},
})

const getTableOptions = createResource({
	method: 'insights.api.get_tables',
	initialData: [],
})
const tableOptions = computed(() =>
	getTableOptions.data.map((table) => ({
		...table,
		value: table.table,
	}))
)
getTableOptions.submit({ data_source: props.name })

const getForeignKeyOptions = createResource({
	method: 'insights.api.get_table_columns',
	initialData: [],
})
watch(
	() => newLink.table,
	(table) => {
		if (table) {
			getForeignKeyOptions.submit({
				data_source: props.name,
				table: table.table,
			})
		} else {
			foreignKeyOptions.value = []
		}
	}
)
const foreignKeyOptions = computed({
	get() {
		return (
			getForeignKeyOptions.data?.columns?.map((c) => {
				return {
					label: `${c.label} (${c.type})`,
					value: c.column,
				}
			}) || []
		)
	},
	set(value) {
		getForeignKeyOptions.data = value
	},
})

const createLinkDisabled = computed(() => {
	return (
		!newLink.table ||
		!(newLink.primaryKey && newLink.primaryKey.value) ||
		!(newLink.foreignKey && newLink.foreignKey.value)
	)
})

const $notify = inject('$notify')
const createLinkResource = createResource({
	method: 'insights.api.create_table_link',
	onSuccess() {
		newLink.table = ''
		newLink.primaryKey = ''
		newLink.foreignKey = ''
		addLinkDialog.value = false
		$notify({
			appearance: 'success',
			title: 'Success',
			message: 'Link created successfully',
		})
	},
})
const creatingLink = computed(() => createLinkResource.loading)

function createLink() {
	if (createLinkDisabled.value) return
	createLinkResource.submit({
		data_source: props.name,
		primary_table: {
			label: doc.value.label,
			table: doc.value.table,
		},
		foreign_table: {
			label: newLink.table.label,
			table: newLink.table.table,
		},
		primary_key: newLink.primaryKey.value,
		foreign_key: newLink.foreignKey.value,
	})
}
</script>
