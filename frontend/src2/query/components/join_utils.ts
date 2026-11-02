import { watchDebounced } from '@vueuse/core'
import { computed, ComputedRef, reactive, Ref, ref, watch } from 'vue'
import useTableStore from '../../data_source/tables'
import { wheneverChanges } from '../../helpers'
import { ColumnOption, JoinArgs } from '../../types/query.types'
import useQuery from '../query'

export function handleOldProps(join: JoinArgs) {
	// handle backward compatibility
	// move left_column and right_column under join_condition
	const _join: any = { ...join }
	if (join && _join.left_column?.column_name && _join.right_column?.column_name) {
		join.join_condition = {
			left_column: _join.left_column,
			right_column: _join.right_column,
		}
		// @ts-ignore
		delete join.left_column
		// @ts-ignore
		delete join.right_column
	}
}

type TableOption = {
	label: string
	value: string
	description: string
	data_source: string
	table_name: string
}
type UseTableOptions = {
	data_source: Ref<string> | ComputedRef<string>
	selected_table?: Ref<string> | ComputedRef<string>
}
export function useTableOptions(options: UseTableOptions) {
	const tableStore = useTableStore()

	function toOption(table_name: string, data_source: string): TableOption {
		return {
			table_name,
			data_source,
			description: data_source,
			label: table_name,
			value: `${data_source}.${table_name}`,
		}
	}

	const tableOptions = computed<TableOption[]>(() => {
		const dataSourceTables = tableStore.tables[options.data_source.value] || []
		const fetched = dataSourceTables.map((t) => toOption(t.table_name, t.data_source))

		// The search never has to hold the selection. A combobox that cannot find
		// its own value falls back to printing it raw, and here the raw value is
		// "<data source>.<table>", which matches no table and keeps the list empty.
		const selected = options.selected_table?.value
		if (selected && !fetched.some((o) => o.table_name === selected)) {
			return [toOption(selected, options.data_source.value), ...fetched]
		}
		return fetched
	})

	const searchText = ref('')
	watchDebounced(
		searchText,
		() => tableStore.getTables(options.data_source.value, searchText.value),
		{
			debounce: 300,
			immediate: true,
		},
	)

	return reactive({
		options: tableOptions,
		loading: tableStore.loading,
		searchText,
	})
}

export function useTableColumnOptions(data_source: Ref<string>, table_name: Ref<string>) {
	const tableColumnOptions = ref<DropdownOption[]>([])
	const fetchingColumnOptions = ref(false)
	const tableStore = useTableStore()

	wheneverChanges(
		table_name,
		() => {
			if (!table_name.value) {
				tableColumnOptions.value = []
				return
			}

			fetchingColumnOptions.value = true
			tableStore
				.getTableColumns(data_source.value, table_name.value)
				.then((columns) => {
					tableColumnOptions.value = columns.map((c: any) => ({
						label: c.name,
						value: c.name,
						description: c.type,
						data_type: c.type,
					}))
				})
				.finally(() => {
					fetchingColumnOptions.value = false
				})
		},
		{ immediate: true },
	)

	return reactive({
		options: tableColumnOptions,
		loading: fetchingColumnOptions,
	})
}

export function useQueryColumnOptions(query_name: Ref<string>) {
	const queryColumnOptions = ref<ColumnOption[]>([])
	const fetchingColumnOptions = ref(false)

	watch(
		query_name,
		(newQueryName, oldQueryName) => {
			// clear option when query changes
			if (newQueryName !== oldQueryName) {
				queryColumnOptions.value = []
			}

			if (!newQueryName) {
				return
			}

			fetchingColumnOptions.value = true
			const query = useQuery(newQueryName)

			query
				.getColumnsForSelection()
				.then((columns) => {
					queryColumnOptions.value = columns
				})
				.catch((error) => {
					console.error('error:', error)
					queryColumnOptions.value = []
				})
				.finally(() => {
					fetchingColumnOptions.value = false
				})
		},
		{ immediate: true },
	)
	return reactive({
		options: queryColumnOptions,
		loading: fetchingColumnOptions,
	})
}
