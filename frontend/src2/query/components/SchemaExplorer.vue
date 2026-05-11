<script setup lang="ts">
import {
	ChevronDown,
	ChevronRight,
	Search,
	Calendar,
	HashIcon,
	SearchIcon,
	TypeIcon,
} from 'lucide-vue-next'
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
	emit('insert-text', `\`${columnName}\`\,`)
}

function getColumnIcon(type: string) {
	const colType = type?.toLowerCase() || ''

	if (colType === 'string') {
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
			column.label.toLowerCase().includes(query),
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
	<div class="flex flex-1 flex-col overflow-hidden px-3.5 py-3">
		<div class="mb-2 flex h-6 flex-shrink-0 items-center justify-between">
			<div class="text-sm font-medium">Tables</div>
		</div>
		<div class="mb-2 flex-shrink-0">
			<FormControl
				placeholder="Search tables and columns..."
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-3.5 w-3.5 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<div class="flex-1 overflow-y-auto text-base">
			<div v-if="!Object.keys(schema).length" class="py-4 text-center text-sm text-gray-500">
				Select a data source to explore tables
			</div>
			<div
				v-else-if="!Object.keys(filteredSchema).length"
				class="py-4 text-center text-sm text-gray-500"
			>
				No tables or columns match your search
			</div>
			<div v-else class="flex flex-col gap-0.5">
				<div
					v-for="[tableName, tableData] in Object.entries(filteredSchema)"
					:key="tableName"
				>
					<div
						class="flex w-full cursor-pointer select-none items-center gap-1.5 rounded py-1.5 text-gray-700 hover:bg-gray-50"
						@click="toggleTable(tableName)"
					>
						<ChevronDown
							v-if="expandedTables.has(tableName)"
							class="h-4 w-4 flex-shrink-0 text-gray-400"
						/>
						<ChevronRight v-else class="h-4 w-4 flex-shrink-0 text-gray-400" />

						<button
							@click.stop="insertTableName(tableName)"
							class="truncate text-start font-medium text-gray-700 hover:text-blue-600"
						>
							{{ tableName }}
						</button>
					</div>
					<div
						v-if="expandedTables.has(tableName)"
						class="ml-3 flex flex-col gap-0.5 py-0.5"
					>
						<button
							v-for="column in tableData.columns"
							:key="column.label"
							@click="insertColumnName(column.label)"
							class="flex w-full items-center gap-1.5 rounded py-1.5 pl-2 text-left text-gray-600 hover:bg-gray-50"
							:title="`${column.label} (${column.detail || column.type})`"
						>
							<component
								:is="getColumnIcon(column.detail || column.type)"
								class="h-4 w-4 flex-shrink-0 text-gray-600"
							/>
							<span class="truncate text-gray-700">{{ column.label }}</span>
							<span class="ml-auto flex-shrink-0 pr-1 text-xs text-gray-500">{{
								column.detail || column.type
							}}</span>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
