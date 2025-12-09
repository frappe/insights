<script setup lang="ts">
import { ChevronDown, ChevronRight, Search, Table2 , Calendar, HashIcon,Link, Image,Mail,TypeIcon} from 'lucide-vue-next'
import { computed, ref } from 'vue'

interface Column {
	label: string
	detail: string
	type: string
}

interface TableSchema {
	[key: string]: {
		label?: string
		columns: Column[]
	}
}

interface Props {
	schema: TableSchema
}

interface Emits {
	(e: 'insert-text', text: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const expandedTables = ref<Set<string>>(new Set())
const searchQuery = ref('')

function toggleTable(tableName: string) {
	if (expandedTables.value.has(tableName)) {
		expandedTables.value.delete(tableName)
	} else {
		expandedTables.value.add(tableName)
	}
}
function insertTableName(tableName: string) {
	emit('insert-text', `\`${tableName}\``)
}

function insertColumnName(columnName: string) {
	emit('insert-text', `\`${columnName}\``)
}

function getColumnIcon(type: string) {
	const colType = type?.toLowerCase() || ''

	if (colType === 'string' ) {
		return TypeIcon
	} else if (colType === 'integer' || colType.includes('decimal')) {
		return HashIcon
	} else if (colType === 'date' || colType === 'datetime' || colType.includes('time')) {
		return Calendar
	} else {
		return TypeIcon
	}
}

const filteredSchema = computed(() => {
	if (!searchQuery.value.trim()) {
		expandedTables.value.clear()
		return props.schema
	}

	const query = searchQuery.value.toLowerCase()
	const filtered: TableSchema = {}

	Object.entries(props.schema).forEach(([tableName, tableData]) => {
		const tableMatches = tableName.toLowerCase().includes(query)
		const matchingColumns = tableData.columns.filter((column) =>
			column.label.toLowerCase().includes(query)
		)

		if (tableMatches || matchingColumns.length > 0) {
			filtered[tableName] = {
				...tableData,
				columns: tableMatches ? tableData.columns : matchingColumns,
			}
			// auto expand tables with matching columns
			if (matchingColumns.length > 0 && !tableMatches) {
				expandedTables.value.add(tableName)
			}
		}
	})

	return filtered
})
</script>

<template>
	<div class="flex h-full flex-col overflow-hidden rounded border bg-white">
		<div class="flex-shrink-0 border-b px-3 py-2 text-sm font-medium text-gray-700">
			Tables
		</div>
		<div class="flex-shrink-0 border-b p-2">
			<div class="relative">
				<Search class="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
				<input
					v-model="searchQuery"
					type="text"
					placeholder="Search tables and columns..."
					class="w-full rounded border border-gray-300 py-1.5 pl-8 pr-3 text-sm focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-400"
				/>
			</div>
		</div>
		<div class="flex-1 overflow-y-auto">
			<div v-if="!Object.keys(schema).length" class="p-4 text-center text-sm text-gray-500">
				No Tables available. Select a data source first
			</div>
			<div v-else-if="!Object.keys(filteredSchema).length" class="p-4 text-center text-sm text-gray-500">
				No tables or columns match your search
			</div>
			<div v-else class="divide-y">
				<div v-for="[tableName, tableData] in Object.entries(filteredSchema)" :key="tableName">
					<div class="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50">
						<button
							@click="toggleTable(tableName)"
							class="flex h-4 w-4 flex-shrink-0 items-center justify-center"
						>
							<ChevronRight
								v-if="!expandedTables.has(tableName)"
								class="h-4 w-4 text-gray-500"
							/>
							<ChevronDown
								v-else
								class="h-4 w-4 text-gray-500"
							/>
						</button>
						<Table2 class="h-5 w-5  text-gray-700" />
						<button
							@click="insertTableName(tableName)"
							class="text-start font-medium text-gray-700 hover:text-blue-600"
						>
							{{ tableName }}
						</button>
					</div>
					<div v-if="expandedTables.has(tableName)" class=" py-1">
						<button
							v-for="column in tableData.columns"
							:key="column.label"
							@click="insertColumnName(column.label)"
							class="flex w-full items-center gap-2 px-4 py-1.5 text-left text-sm text-gray-600 hover:bg-gray-100 hover:text-blue-600"
							:title="`${column.label} (${column.detail || column.type})`"
						>
							<component
								:is="getColumnIcon(column.detail || column.type)"
								class="h-4 w-4 flex-shrink-0 text-gray-700"
							/>

							<span class="truncate text-gray-700 hover:text-blue-600">{{ column.label }}</span>
							<span class="ml-auto flex-shrink-0 text-xs text-gray-500">{{ column.detail || column.type }}</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
