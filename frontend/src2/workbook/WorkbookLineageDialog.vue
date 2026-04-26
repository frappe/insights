<script setup lang="ts">
import { MarkerType, Panel, Position, VueFlow, useVueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { FormControl } from 'frappe-ui'
import { BarChart2, DatabaseIcon, GitFork } from 'lucide-vue-next'
import { computed, inject, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { __ } from '../translation'
import { Workbook, workbookKey } from './workbook'

const show = defineModel<boolean>()

const workbook = inject(workbookKey) as Workbook
const router = useRouter()
const { fitView } = useVueFlow()

// ── State ─────────────────────────────────────────────────────────────────────
const loading = ref(true)
const searchQuery = ref('')

type RawNode = {
	id: string
	node_type: 'table' | 'query'
	label: string
	name?: string
	workbook?: string
	data_source?: string
	chart_title?: string
}
type RawEdge = { id: string; source: string; target: string }

const allNodes = ref<RawNode[]>([])
const allEdges = ref<RawEdge[]>([])

onMounted(async () => {
	const result = await workbook.call('get_lineage_graph')
	allNodes.value = result.nodes
	allEdges.value = result.edges
	loading.value = false
	await nextTick()
	fitView({ padding: 0.15, duration: 400 })
})

// ── Search filtering ──────────────────────────────────────────────────────────
const visibleNodeIds = computed(() => {
	const base = new Set(allNodes.value.map((n) => n.id))
	if (!searchQuery.value.trim()) return base
	const q = searchQuery.value.toLowerCase()
	const matched = new Set(
		allNodes.value
			.filter(
				(n) =>
					n.label.toLowerCase().includes(q) ||
					n.id.toLowerCase().includes(q) ||
					(n.chart_title?.toLowerCase().includes(q) ?? false),
			)
			.map((n) => n.id),
	)
	return new Set([...base].filter((id) => matched.has(id)))
})

const visibleNodes = computed(() => allNodes.value.filter((n) => visibleNodeIds.value.has(n.id)))
const visibleEdges = computed(() =>
	allEdges.value.filter(
		(e) => visibleNodeIds.value.has(e.source) && visibleNodeIds.value.has(e.target),
	),
)

// ── Layout ────────────────────────────────────────────────────────────────────
function computeLayout(nodes: RawNode[], edges: RawEdge[]): Map<string, { x: number; y: number }> {
	const levelMap = new Map<string, number>()
	nodes.forEach((n) => levelMap.set(n.id, 0))

	let changed = true
	while (changed) {
		changed = false
		edges.forEach((e) => {
			const sl = levelMap.get(e.source) ?? 0
			const tl = levelMap.get(e.target) ?? 0
			if (tl < sl + 1) {
				levelMap.set(e.target, sl + 1)
				changed = true
			}
		})
	}

	const byLevel = new Map<number, string[]>()
	levelMap.forEach((level, id) => {
		if (!byLevel.has(level)) byLevel.set(level, [])
		byLevel.get(level)!.push(id)
	})
	const nodeLabel = new Map(nodes.map((n) => [n.id, n.label]))
	byLevel.forEach((ids) =>
		ids.sort((a, b) => (nodeLabel.get(a) ?? '').localeCompare(nodeLabel.get(b) ?? '')),
	)

	const positions = new Map<string, { x: number; y: number }>()
	const COL_WIDTH = 280
	const ROW_HEIGHT = 88
	byLevel.forEach((ids, level) => {
		ids.forEach((id, i) => positions.set(id, { x: level * COL_WIDTH, y: i * ROW_HEIGHT }))
	})
	return positions
}

// ── Vue Flow nodes/edges ──────────────────────────────────────────────────────
const vfNodes = computed(() => {
	const positions = computeLayout(visibleNodes.value, visibleEdges.value)
	return visibleNodes.value.map((n) => ({
		id: n.id,
		type: n.node_type,
		position: positions.get(n.id) ?? { x: 0, y: 0 },
		sourcePosition: Position.Right,
		targetPosition: Position.Left,
		data: n,
		selectable: true,
	}))
})

const vfEdges = computed(() =>
	visibleEdges.value.map((e) => ({
		id: e.id,
		source: e.source,
		target: e.target,
		type: 'smoothstep',
		markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: '#94a3b8' },
		style: { stroke: '#cbd5e1', strokeWidth: 1.5 },
	})),
)

// ── Navigation ────────────────────────────────────────────────────────────────
function onNodeClick(_evt: MouseEvent, node: any) {
	const data: RawNode = node.data
	if (data.node_type === 'query' && data.name) {
		show.value = false
		router.push({
			name: 'WorkbookQuery',
			params: { workbook_name: workbook.doc.name, query_name: data.name },
		})
	}
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Query Lineage'),
			size: '5xl',
		}"
	>
		<template #body-content>
			<!-- Toolbar -->
			<div class="mb-3 flex items-center gap-2">
				<span class="text-sm text-gray-500">
					{{ visibleNodes.length }} {{ __('nodes') }}, {{ visibleEdges.length }}
					{{ __('edges') }}
				</span>
				<div class="ml-auto">
					<FormControl
						v-model="searchQuery"
						:placeholder="__('Search nodes\u2026')"
						autocomplete="off"
					>
						<template #prefix>
							<FeatherIcon name="search" class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
				</div>
			</div>

			<!-- Canvas -->
			<div class="relative h-[520px] overflow-hidden rounded-lg border border-gray-200">
				<div
					v-if="loading"
					class="absolute inset-0 z-10 flex items-center justify-center bg-white/80"
				>
					<div class="text-sm text-gray-400">{{ __('Loading\u2026') }}</div>
				</div>

				<VueFlow
					:nodes="vfNodes"
					:edges="vfEdges"
					:nodes-connectable="false"
					:edges-updatable="false"
					:delete-key-code="null"
					fit-view-on-init
					class="bg-gray-50"
					@node-click="onNodeClick"
				>
					<Panel
						position="top-right"
						class="rounded border border-gray-200 bg-white p-2 shadow-sm"
					>
						<div class="flex flex-col gap-1.5">
							<div class="flex items-center gap-2">
								<span
									class="size-2.5 rounded-full bg-blue-100 border border-blue-200"
								></span>
								<span class="text-sm text-gray-600">{{ __('Table') }}</span>
							</div>
							<div class="flex items-center gap-2">
								<span
									class="size-2.5 rounded-full bg-green-100 border border-green-200"
								></span>
								<span class="text-sm text-gray-600">{{ __('Query') }}</span>
							</div>
							<div class="flex items-center gap-2">
								<span
									class="size-2.5 rounded-full bg-orange-100 border border-orange-200"
								></span>
								<span class="text-sm text-gray-600">{{ __('Chart') }}</span>
							</div>
						</div>
					</Panel>

					<!-- Table node -->
					<template #node-table="{ data }">
						<div
							class="flex w-52 flex-col gap-0.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 shadow-sm"
						>
							<div class="flex items-center gap-1.5">
								<DatabaseIcon
									class="h-3.5 w-3.5 flex-shrink-0 text-blue-500"
									stroke-width="1.5"
								/>
								<span class="truncate text-sm font-medium text-blue-900">{{
									data.label
								}}</span>
							</div>
							<span class="truncate pl-5 text-xs text-blue-500">{{
								data.data_source
							}}</span>
						</div>
					</template>

					<!-- Query node -->
					<template #node-query="{ data }">
						<div
							class="flex w-52 flex-col gap-0.5 rounded-lg border px-3 py-2.5 shadow-sm transition-shadow hover:shadow-md"
							:class="[
								data.is_chart_query
									? 'border-orange-200 bg-orange-50'
									: 'border-green-200 bg-green-50',
								{ 'cursor-pointer': data.name },
							]"
						>
							<div class="flex items-center gap-1.5">
								<component
									:is="data.is_chart_query ? BarChart2 : GitFork"
									class="h-3.5 w-3.5 flex-shrink-0"
									:class="
										data.is_chart_query ? 'text-orange-600' : 'text-green-600'
									"
									stroke-width="1.5"
								/>
								<span
									class="truncate text-sm font-medium"
									:class="
										data.is_chart_query ? 'text-orange-900' : 'text-green-900'
									"
									>{{ data.is_chart_query ? data.chart_title : data.label }}</span
								>
							</div>
						</div>
					</template>
				</VueFlow>
			</div>
		</template>
	</Dialog>
</template>
