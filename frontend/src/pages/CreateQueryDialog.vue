<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { createResource } from 'frappe-ui'
import { computed, reactive, watch } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: {
		type: Boolean,
		required: true,
	},
})
const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const newQuery = reactive({
	dataSource: '',
	title: 'Untitled',
	table: null,
})
const getDataSources = createResource({
	url: 'insights.api.get_data_sources',
	auto: true,
	onSuccess(res) {
		if (res.length) {
			newQuery.dataSource = res[0].name
		}
	},
})
const dataSources = computed(() => {
	return getDataSources.data?.map((d) => d['name']) || []
})
const getTableOptions = createResource({
	url: 'insights.api.get_tables',
	initialData: [],
})
const tableOptions = computed(() =>
	getTableOptions.data.map((table) => ({
		...table,
		value: table.table,
	}))
)
watch(
	() => newQuery.dataSource,
	(data_source, old) => {
		if (data_source !== old) {
			getTableOptions.submit({ data_source })
		}
	}
)

const createQuery = createResource({
	url: 'insights.api.create_query',
	onSuccess(name) {
		newQuery.title = ''
		newQuery.dataSource = ''
		show.value = false
		emit('create', name)
	},
})

const createDisabled = computed(() => {
	return !newQuery.dataSource || !newQuery.table || !newQuery.title
})
const submitQuery = () => {
	if (!createDisabled.value) {
		createQuery.submit({
			title: newQuery.title,
			data_source: newQuery.dataSource,
			table: newQuery.table,
		})
	}
}
</script>

<template>
	<Dialog :options="{ title: 'New Query' }" v-model="show">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="select"
					label="Data Source"
					v-model="newQuery.dataSource"
					:options="dataSources"
				/>
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">Table</div>
					<Autocomplete
						v-model="newQuery.table"
						:options="tableOptions"
						placeholder="Select a table..."
					/>
				</div>
				<Input
					type="text"
					label="Title"
					v-model="newQuery.title"
					placeholder="Enter a suitable title..."
				/>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				@click="submitQuery"
				:disabled="createDisabled"
				:loading="createQuery.loading"
			>
				Create
			</Button>
		</template>
	</Dialog>
</template>
