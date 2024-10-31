import { watchDebounced } from '@vueuse/core'
import { computed, ComputedRef, reactive, Ref, ref } from 'vue'
import useTableStore from '../../data_source/tables'
import { wheneverChanges } from '../../helpers'
import { JoinArgs } from '../../types/query.types'

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
	initialSearchText?: string
}
export function useTableOptions(options: UseTableOptions) {
	const tableStore = useTableStore()

	const tableOptions = computed<TableOption[]>(() => {
		const dataSourceTables = tableStore.tables[options.data_source.value] || []
		if (!dataSourceTables.length) return []

		return dataSourceTables.map((t) => ({
			table_name: t.table_name,
			data_source: t.data_source,
			description: t.data_source,
			label: t.table_name,
			value: `${t.data_source}.${t.table_name}`,
		}))
	})

	const searchText = ref(options.initialSearchText || '')
	watchDebounced(
		searchText,
		() => tableStore.getTables(options.data_source.value, searchText.value),
		{
			debounce: 300,
			immediate: true,
		}
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
		{ immediate: true }
	)

	return reactive({
		options: tableColumnOptions,
		loading: fetchingColumnOptions,
	})
}
