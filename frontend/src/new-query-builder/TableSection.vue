<script setup>
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import useDataSource from '@/datasource/useDataSource'
import { whenever } from '@vueuse/core'
import { computed, inject } from 'vue'

const query = inject('query')
const builder = inject('builder')

const dataSource = useDataSource(query.doc.data_source)
dataSource.fetchTables()
whenever(
	() => query.doc.data_source,
	(newVal, oldVal) => {
		if (newVal == oldVal) return
		dataSource = useDataSource(query.doc.data_source)
		dataSource.fetchTables()
	}
)
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
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 text-sm hover:shadow"
			>
				<div>{{ builder.query.table.label }}</div>
			</div>
			<div
				v-for="join in builder.query.joins"
				:key="join.right_table.table"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 text-sm hover:shadow"
			>
				<div>{{ join.right_table.label }}</div>
				<JoinLeftIcon class="text-gray-600" />
			</div>
		</div>
	</div>
</template>
