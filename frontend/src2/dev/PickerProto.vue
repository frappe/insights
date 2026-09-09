<script setup lang="ts">
// PROTOTYPE — throwaway. See docs/projects/table-experience/issues/01-filter-picker.md
//
// The conditions live on the popover's own overview step, and the trigger
// carries their count. One page, one popover.

import { Badge } from 'frappe-ui'
import { computed, ref } from 'vue'
import useQuery from '../query/query'
import type { QueryResultColumn } from '../types/query.types'
import ProtoFilter from './ProtoFilter.vue'
import { type ProtoFilter as ProtoFilterRule } from './proto_filter'

// --- data ------------------------------------------------------------------

const QUERY_NAME = 'paid_invoices'
const query = useQuery(QUERY_NAME)
const loadError = ref('')
query.ensureResult().catch((e: any) => (loadError.value = String(e?.message || e)))

// only used when the real query cannot load — so the picker is still walkable
const FALLBACK_COLUMNS: QueryResultColumn[] = [
	{ name: 'customer', type: 'String' },
	{ name: 'territory', type: 'String' },
	{ name: 'status', type: 'String' },
	{ name: 'posting_date', type: 'Date' },
	{ name: 'grand_total', type: 'Decimal' },
	{ name: 'outstanding_amount', type: 'Decimal' },
]

const columns = computed<QueryResultColumn[]>(() => {
	const cols = query.result?.columns
	return cols?.length ? cols : FALLBACK_COLUMNS
})

function valuesProvider(column: QueryResultColumn) {
	return (search: string): Promise<string[]> => {
		if (!query.result?.columns?.length) return Promise.resolve([])
		return query.getDistinctColumnValues(column.name, search).catch(() => [])
	}
}

// --- filters ---------------------------------------------------------------

const filters = ref<ProtoFilterRule[]>([])

// what the picker would hand a host: Insights' FilterArgs, one per condition
const filterArgs = computed(() =>
	JSON.stringify(
		filters.value.map((f) => ({
			column: { type: 'column', column_name: f.column.name },
			operator: f.operator,
			value: f.value,
		})),
		null,
		2,
	),
)
</script>

<template>
	<div class="flex h-full flex-col overflow-hidden bg-surface-base p-6">
		<div class="flex items-center gap-2">
			<span class="text-p-base font-medium text-ink-gray-8">Paid invoices</span>
			<Badge v-if="loadError" theme="amber" variant="subtle" size="lg">
				fallback columns — {{ loadError }}
			</Badge>

			<div class="flex-1"></div>

			<ProtoFilter v-model="filters" :columns="columns" :values-provider="valuesProvider" />
		</div>

		<pre
			class="mt-4 flex-1 overflow-auto rounded border border-outline-gray-2 bg-surface-gray-1 p-3 text-p-sm text-ink-gray-7"
			>{{ filterArgs }}</pre
		>
	</div>
</template>
