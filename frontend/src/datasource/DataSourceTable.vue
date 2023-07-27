<template>
	<div class="flex h-full w-full flex-col bg-white px-8 py-4">
		<Breadcrumbs
			:items="[
				{
					label: 'Data Sources',
					href: '/data-source',
				},
				{
					label: props.name,
					href: `/data-source/${props.name}`,
				},
				{
					label: dataSourceTable.doc?.label || props.table,
					href: `/data-source/${props.name}/${props.table}`,
				},
			]"
		/>

		<div v-if="dataSourceTable.doc" class="mt-2 flex items-center space-x-4">
			<div class="flex items-start space-x-4">
				<h1 class="text-3xl font-medium text-gray-900">
					{{ dataSourceTable.doc.label }}
				</h1>
				<div class="flex h-8 items-center">
					<Badge :theme="hidden ? 'yellow' : 'green'" size="lg">
						{{ hidden ? 'Disabled' : 'Enabled' }}
					</Badge>
				</div>
			</div>
			<div class="space-x-2">
				<Dropdown
					placement="left"
					:button="{
						icon: 'more-horizontal',
						variant: 'ghost',
					}"
					:options="[
						{
							label: hidden ? 'Enable' : 'Disable',
							icon: hidden ? 'eye' : 'eye-off',
							onClick: () => (hidden = !hidden),
						},
						{
							label: 'Sync Table',
							icon: 'refresh-cw',
							onClick: () => dataSourceTable.sync(),
						},
						{
							label: 'Add Link',
							icon: 'link',
							onClick: () => (addLinkDialog = true),
						},
					]"
				/>
			</div>
		</div>
		<div
			v-if="
				dataSourceTable.doc &&
				dataSourceTable.doc.columns &&
				dataSourceTable.rows?.data &&
				!dataSourceTable.syncing
			"
			class="flex flex-1 flex-col overflow-hidden pt-3"
		>
			<div class="flex h-6 flex-shrink-0 space-x-1 text-sm font-light text-gray-600">
				{{ dataSourceTable.doc.columns.length }} Columns -
				{{ dataSourceTable.rows.length }} Rows
			</div>
			<div class="flex flex-1 overflow-scroll">
				<Grid :header="true" :rows="dataSourceTable.rows.data">
					<template #header>
						<DataSourceTableColumnHeader
							:columns="dataSourceTable.doc.columns"
							@update-column-type="dataSourceTable.updateColumnType"
						/>
					</template>
				</Grid>
			</div>
		</div>
		<div
			v-else
			class="mt-2 flex h-full w-full flex-col items-center justify-center rounded bg-gray-50"
		>
			<LoadingIndicator class="mb-2 w-8 text-gray-500" />
			<div class="text-lg text-gray-600">Syncing columns from database...</div>
		</div>
	</div>

	<Dialog :options="{ title: 'Create a Link' }" v-model="addLinkDialog">
		<template #body-content>
			<div class="space-y-4">
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">Table</div>
					<Autocomplete
						ref="$autocomplete"
						v-model="newLink.table"
						:options="tableOptions"
						placeholder="Select a table..."
					/>
				</div>
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">
						Select a column from {{ dataSourceTable.doc.label }}
					</div>
					<Autocomplete
						v-model="newLink.primaryKey"
						:options="
							dataSourceTable.doc.columns.map((c) => ({
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
				variant="solid"
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
import Grid from '@/components/Grid.vue'
import DataSourceTableColumnHeader from './DataSourceTableColumnHeader.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { useDataSourceTable } from '@/datasource/useDataSource'
import { Dropdown, Badge, createResource, LoadingIndicator } from 'frappe-ui'
import { computed, ref, reactive, watch, inject, nextTick } from 'vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'

const props = defineProps({
	name: {
		// data source name
		type: String,
		required: true,
	},
	table: {
		// table name
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

const dataSourceTable = await useDataSourceTable({ name: props.table })
dataSourceTable.fetchPreview()
const hidden = computed({
	get() {
		return dataSourceTable.doc.hidden
	},
	set(value) {
		if (value !== dataSourceTable.hidden) {
			dataSourceTable.updateVisibility.submit({
				hidden: value,
			})
		}
	},
})

const getTableOptions = createResource({
	url: 'insights.api.get_tables',
	params: {
		data_source: props.name,
	},
	initialData: [],
	auto: true,
})
const tableOptions = computed(() =>
	getTableOptions.data.map((table) => ({
		...table,
		value: table.table,
	}))
)

const getForeignKeyOptions = createResource({
	url: 'insights.api.get_table_columns',
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
	url: 'insights.api.create_table_link',
	onSuccess() {
		newLink.table = ''
		newLink.primaryKey = ''
		newLink.foreignKey = ''
		addLinkDialog.value = false
		$notify({
			variant: 'success',
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
			label: dataSourceTable.doc.label,
			table: dataSourceTable.doc.table,
		},
		foreign_table: {
			label: newLink.table.label,
			table: newLink.table.table,
		},
		primary_key: newLink.primaryKey.value,
		foreign_key: newLink.foreignKey.value,
	})
}

const $autocomplete = ref(null)
watch(addLinkDialog, async (val) => {
	if (val) {
		await nextTick()
		setTimeout(() => {
			$autocomplete.value.input.$el.blur()
			$autocomplete.value.input.$el.focus()
		}, 500)
	}
})
</script>
