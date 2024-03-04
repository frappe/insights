import { call } from 'frappe-ui'
import { ref } from 'vue'
import {
	filter,
	join,
	limit,
	mutate,
	order_by,
	pivot_wider,
	source,
	summarize,
} from './pipeline_utils'

function useQueryPipeline() {
	const steps = ref<PipelineStep[]>([])
	const activeStepIndex = ref(-1)
	const executing = ref(false)
	const results = ref<Record<string, any>[]>([])

	// watch(steps, execute, { deep: true })
	function execute(tillStep?: number) {
		activeStepIndex.value = typeof tillStep === 'number' ? tillStep : steps.value.length - 1
		const _steps = steps.value.slice(0, activeStepIndex.value + 1)

		executing.value = true
		return call('insights.api.queries.execute_query_pipeline', { query_pipeline: _steps })
			.then((response: any) => {
				results.value = response
			})
			.finally(() => {
				executing.value = false
			})
	}

	return {
		steps,
		activeStepIndex,
		results,
		executing,
		execute,
		setPipeline(pipeline: PipelineStep[]) {
			steps.value = pipeline
		},
		addSource: (sourceArgs: SourceArgs) => steps.value.push(source(sourceArgs)),
		addJoin: (joinArgs: JoinArgs) => steps.value.push(join(joinArgs)),
		addFilter: (filterArgs: FilterArgs) => steps.value.push(filter(filterArgs)),
		addMutate: (mutateArgs: MutateArgs) => steps.value.push(mutate(mutateArgs)),
		addSummarize: (summarizeArgs: SummarizeArgs) => steps.value.push(summarize(summarizeArgs)),
		addOrderBy: (orderByArgs: OrderByArgs) => steps.value.push(order_by(orderByArgs)),
		addLimit: (row_count: number) => steps.value.push(limit(row_count)),
		addPivotWider: (pivotWiderArgs: PivotWiderArgs) =>
			steps.value.push(pivot_wider(pivotWiderArgs)),
	}
}

export type QueryPipeline = ReturnType<typeof useQueryPipeline>
export default useQueryPipeline
