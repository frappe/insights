<template>
	<header class="sticky top-0 z-10 flex items-center bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{
					label: 'Data Sources',
					href: '/data-source',
					route: { path: '/data-source' },
				},
				{
					label: props.name,
					route: { path: `/data-source/${props.name}` },
				},
				{
					label: dataSourceTable.doc?.label || props.table,
				},
			]"
		/>
		<div v-if="dataSourceTable.doc" class="ml-2 flex items-center space-x-2.5">
			<Badge variant="subtle" :theme="hidden ? 'gray' : 'green'" size="md">
				{{ hidden ? 'Disabled' : 'Enabled' }}
			</Badge>
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
	</header>
	<div class="flex flex-1 flex-col overflow-hidden bg-white px-6 py-2">
		<div
			v-if="
				dataSourceTable.doc &&
				dataSourceTable.doc.columns &&
				dataSourceTable.rows?.data &&
				!dataSourceTable.syncing
			"
			class="flex flex-1 flex-col overflow-hidden"
		>
			<!-- <div class="flex h-6 flex-shrink-0 space-x-1 text-sm font-light text-gray-600">
				{{ dataSourceTable.doc.columns.length }} Columns -
				{{ dataSourceTable.rows.length }} Rows
			</div> -->
			<div class="flex flex-1 overflow-auto">
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
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { Badge, Dropdown, LoadingIndicator, createResource } from 'frappe-ui'
import { computed, inject, nextTick, reactive, ref, watch, watchEffect } from 'vue'
import DataSourceTableColumnHeader from './DataSourceTableColumnHeader.vue'

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
			dataSourceTable.updateVisibility(Boolean(value))
		}
	},
})

const getTableOptions = createResource({
	url: 'insights.api.data_sources.get_tables',
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
	url: 'insights.api.data_sources.get_table_columns',
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
	url: 'insights.api.data_sources.create_table_link',
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

watchEffect(() => {
	if (dataSourceTable.doc?.label) {
		const title = dataSourceTable.doc.title || dataSourceTable.doc.label
		document.title = `${title} - Frappe Insights`
	}
})
</script>
