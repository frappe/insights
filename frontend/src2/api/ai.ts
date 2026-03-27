import { call } from 'frappe-ui'
import type { Operation } from '../types/query.types'

export type GenerateQueryRequest = {
	question: string
	data_source: string
	table_names: string[]
	current_operations?: Operation[]
	debug?: boolean
}

export type GenerateQueryResponse = {
	operations: Operation[] | null
	attempts: number
	error: string | null
	debug_log?: string[]
}

export function generateQuery(params: GenerateQueryRequest) {
	return call<GenerateQueryResponse>('insights.api.ai.generate_query', params).then(
		(res: GenerateQueryResponse) => {
			if (res.debug_log?.length) {
				console.groupCollapsed(`[AI debug] ${params.question}`)
				res.debug_log.forEach((line) => console.log(line))
				console.groupEnd()
			}
			return res
		},
	)
}
