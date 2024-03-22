import { fieldtypesToIcon } from '@/utils'
import { confirmDialog } from '@/utils/components'
import { call } from 'frappe-ui'
import { computed, reactive, watch } from 'vue'
import {
	cast,
	column,
	expression,
	filter,
	join,
	limit,
	mutate,
	order_by,
	pivot_wider,
	rename,
	select,
	remove,
	source,
	summarize,
	table,
} from './pipeline_utils'

export type QueryPipelineResultColumn = { name: string; type: keyof typeof fieldtypesToIcon }
export type QueryPipelineResultRow = any[]
export type QueryPipelineResult = {
	rows: QueryPipelineResultRow[]
	columns: QueryPipelineResultColumn[]
	columnOptions: DropdownOption[]
}

function useQueryPipeline() {
	const pipeline = reactive({
		dataSource: '',
		steps: [] as PipelineStep[],
		currentSteps: computed(() => [] as PipelineStep[]),
		activeStepIndex: -1,
		executing: false,
		results: {
			rows: [],
			columns: [],
			columnOptions: [],
		} as QueryPipelineResult,
		execute,
		setPipeline,
		setSource,
		setDataSource,
		addSource,
		addJoin,
		addFilter,
		addMutate,
		addSummarize,
		addOrderBy,
		removeOrderBy,
		addLimit,
		addPivotWider,
		renameColumn,
		removeColumn,
		changeColumnType,

		getDistinctColumnValues,
		getMinAndMax,
	})

	// @ts-ignore
	pipeline.currentSteps = computed<PipelineStep[]>(() => {
		return pipeline.steps.slice(0, pipeline.activeStepIndex + 1)
	})
	watch(
		() => pipeline.currentSteps,
		() => execute(),
		{ deep: true }
	)
	function execute(tillStep?: number) {
		if (!pipeline.dataSource) throw new Error('Data source not set')
		if (!pipeline.steps.length) throw new Error('No steps in pipeline')

		pipeline.activeStepIndex = typeof tillStep === 'number' ? tillStep : pipeline.steps.length - 1

		pipeline.executing = true
		return call('insights.api.queries.execute_query_pipeline', {
			data_source: pipeline.dataSource,
			query_pipeline: pipeline.currentSteps,
		})
			.then((response: any) => {
				pipeline.results.columns = response[0].map((c: any) => ({ name: c.label, type: c.type }))
				pipeline.results.rows = response.slice(1)
				pipeline.results.columnOptions = pipeline.results.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
				}))
			})
			.finally(() => {
				pipeline.executing = false
			})
	}

	type setSourceArgs = { table: string; data_source: string }
	function setSource(args: setSourceArgs) {
		const _setSource = () => {
			pipeline.setPipeline([])
			pipeline.setDataSource(args.data_source)
			pipeline.addSource({ table: table(args.table) })
		}
		if (!pipeline.dataSource || !pipeline.steps.length) {
			_setSource()
			return
		}
		confirmDialog({
			title: 'Change Source',
			message: 'Changing the source will clear the current pipeline. Please confirm.',
			onSuccess: _setSource,
		})
	}

	function setDataSource(data_source: string) {
		pipeline.dataSource = data_source
	}

	function addSource(args: SourceArgs) {
		pipeline.steps.push(source(args))
	}

	function addJoin(args: JoinArgs) {
		pipeline.steps.push(join(args))
	}

	function addFilter(args: FilterArgs) {
		pipeline.steps.push(filter(args))
	}

	function addMutate(args: MutateArgs) {
		pipeline.steps.push(mutate(args))
	}

	function addSummarize(args: SummarizeArgs) {
		pipeline.steps.push(summarize(args))
	}

	function addOrderBy(args: OrderByArgs) {
		const existingOrderBy = pipeline.steps.find(
			(step) =>
				step.type === 'order_by' &&
				step.column.column_name === args.column.column_name &&
				step.direction === args.direction
		)
		if (existingOrderBy) return

		const existingOrderByIndex = pipeline.steps.findIndex(
			(step) => step.type === 'order_by' && step.column.column_name === args.column.column_name
		)
		if (existingOrderByIndex > -1) {
			pipeline.steps[existingOrderByIndex] = order_by(args)
		} else {
			pipeline.steps.push(order_by(args))
		}
	}

	function removeOrderBy(column_name: string) {
		const index = pipeline.steps.findIndex(
			(step) => step.type === 'order_by' && step.column.column_name === column_name
		)
		if (index > -1) {
			pipeline.steps.splice(index, 1)
		}
	}

	function addLimit(args: number) {
		pipeline.steps.push(limit(args))
	}

	function addPivotWider(args: PivotWiderArgs) {
		pipeline.steps.push(pivot_wider(args))
	}

	function renameColumn(oldName: string, newName: string) {
		pipeline.steps.push(
			rename({
				column: column(oldName),
				new_name: newName,
			})
		)
	}

	function removeColumn(column_name: string) {
		pipeline.steps.push(remove({ column_names: [column_name] }))
	}

	function changeColumnType(column_name: string, newType: string) {
		pipeline.steps.push(
			cast({
				column: column(column_name),
				data_type: newType,
			})
		)
	}

	function setPipeline(newPipeline: PipelineStep[]) {
		pipeline.steps = newPipeline
		pipeline.activeStepIndex = newPipeline.length - 1
	}

	function getDistinctColumnValues(column: string, search_term: string = '') {
		return call('insights.api.queries.get_distinct_column_values', {
			data_source: pipeline.dataSource,
			query_pipeline: pipeline.currentSteps,
			column_name: column,
			search_term,
		})
	}
	function getMinAndMax(column: string) {
		return call('insights.api.queries.get_min_max', {
			data_source: pipeline.dataSource,
			query_pipeline: pipeline.currentSteps,
			column_name: column,
		})
	}

	return pipeline
}

export type QueryPipeline = ReturnType<typeof useQueryPipeline>
export default useQueryPipeline
