<script setup lang="ts">
// PROTOTYPE — throwaway. Helpdesk's Filter.vue, trimmed to Insights' columns.
//
// Three steps in one popover: overview (the active conditions), fields (the
// column list), value (one complete picker per type). Opening lands on the
// overview when conditions exist, on the fields list otherwise.

import { useEventListener } from '@vueuse/core'
import { Button, Popover, Tooltip } from 'frappe-ui'
import { ArrowLeftRight, ChevronLeft, ListFilter, Plus, Trash2, X } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import type { FilterOperator, FilterValue, QueryResultColumn } from '../types/query.types'
import ProtoFilterFieldList from './ProtoFilterFieldList.vue'
import ProtoFilterValueEditor from './ProtoFilterValueEditor.vue'
import { columnIcon, kindOf, summaryParts, type ProtoFilter } from './proto_filter'

defineProps<{
	columns: QueryResultColumn[]
	valuesProvider: (column: QueryResultColumn) => (search: string) => Promise<string[]>
}>()

const filters = defineModel<ProtoFilter[]>({ default: () => [] })

const isOpen = ref(false)
const step = ref<'overview' | 'fields' | 'value'>('fields')
const selectedColumn = ref<QueryResultColumn | null>(null)
const editingId = ref<number | null>(null)
// The row a "Replace" targets. The old condition stays untouched until a new one
// is chosen, so backing out leaves the original intact.
const replacingId = ref<number | null>(null)
const editSession = ref(0)
// Where the value editor was opened from, so "back" returns there.
const valueEditorOrigin = ref<'overview' | 'fields'>('overview')
const overviewHeader = ref<HTMLElement | null>(null)

let nextId = 1

const revealOnRowActivity =
	'opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:none)]:opacity-100'

const stepOrder = { overview: 0, fields: 1, value: 2 } as const
const direction = ref<'forward' | 'back'>('forward')

const headerLabel = computed(() => {
	if (step.value === 'overview') return 'Filters'
	if (step.value === 'fields') return 'Choose a column'
	return selectedColumn.value?.name || ''
})

const canGoBack = computed(() => {
	if (step.value === 'value') return true
	return step.value === 'fields' && filters.value.length > 0
})

const editingFilter = computed(() =>
	editingId.value === null ? null : filters.value.find((f) => f.id === editingId.value) || null,
)

function resetSteps() {
	step.value = filters.value.length ? 'overview' : 'fields'
	selectedColumn.value = null
	editingId.value = null
	replacingId.value = null
}

function onOpenChange(open: boolean) {
	isOpen.value = open
	if (open) resetSteps()
}

// The popover auto-focuses its first focusable element, which would put a focus
// ring on the first row. Pull focus to the (non-tabbable) header instead.
function focusOverview() {
	nextTick(() => overviewHeader.value?.focus({ preventScroll: true }))
}

function addNewFilter() {
	replacingId.value = null
	step.value = 'fields'
}

function selectColumn(column: QueryResultColumn) {
	selectedColumn.value = column
	editingId.value = null
	valueEditorOrigin.value = 'fields'
	editSession.value++
	step.value = 'value'
}

function replaceFilter(filter: ProtoFilter) {
	replacingId.value = filter.id
	step.value = 'fields'
}

function editFilter(filter: ProtoFilter) {
	selectedColumn.value = filter.column
	editingId.value = filter.id
	replacingId.value = null
	valueEditorOrigin.value = 'overview'
	editSession.value++
	step.value = 'value'
}

function applyFilter(operator: FilterOperator, value: FilterValue) {
	if (!selectedColumn.value) return
	const targetId = replacingId.value ?? editingId.value
	const existing = targetId === null ? -1 : filters.value.findIndex((f) => f.id === targetId)
	if (existing === -1) {
		const filter: ProtoFilter = {
			id: nextId++,
			column: selectedColumn.value,
			operator,
			value,
		}
		filters.value = [...filters.value, filter]
		editingId.value = filter.id
	} else {
		const next = [...filters.value]
		next[existing] = { id: targetId!, column: selectedColumn.value, operator, value }
		filters.value = next
		editingId.value = targetId
	}
	replacingId.value = null
}

function clearCurrentFilter() {
	if (editingId.value === null) return
	removeFilter(editingId.value)
	editingId.value = null
}

function removeFilter(id: number) {
	filters.value = filters.value.filter((f) => f.id !== id)
}

function clearFilters() {
	filters.value = []
}

function goBack() {
	if (step.value === 'value') {
		step.value = valueEditorOrigin.value
		return
	}
	step.value = filters.value.length ? 'overview' : 'fields'
}

watch(step, (to, from) => {
	direction.value = stepOrder[to] >= stepOrder[from] ? 'forward' : 'back'
})

watch(filters, (list) => {
	if (step.value === 'overview' && !list.length) step.value = 'fields'
})

// F opens the picker. A on the overview jumps to the column list.
useEventListener(document, 'keydown', (event: KeyboardEvent) => {
	if (event.metaKey || event.ctrlKey || event.altKey) return
	const el = document.activeElement
	if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return
	if (!isOpen.value && (event.key === 'f' || event.key === 'F')) {
		event.preventDefault()
		onOpenChange(true)
		return
	}
	if (isOpen.value && step.value === 'overview' && (event.key === 'a' || event.key === 'A')) {
		event.preventDefault()
		addNewFilter()
	}
})

// The calendar needs a sidebar beside it, so the date step is the one panel
// that does not fit the popover's resting width.
const panelWidth = computed(() =>
	step.value === 'value' && selectedColumn.value && kindOf(selectedColumn.value.type) === 'date'
		? 'w-[23rem]'
		: 'w-80',
)
</script>

<template>
	<Popover :open="isOpen" @update:open="onOpenChange" side="bottom" align="end" bare>
		<template #trigger="{ toggle }">
			<!-- A host that owns its toolbar renders the trigger. The built-in one
			     is the fallback. -->
			<slot name="trigger" :count="filters.length" :toggle="toggle" :clear="clearFilters">
				<div class="flex w-fit items-center">
					<Button label="Filter" :class="filters.length ? 'rounded-e-none' : ''">
						<template #prefix>
							<ListFilter class="size-4" stroke-width="1.5" />
						</template>
						<template v-if="filters.length" #suffix>
							<span
								class="flex h-5 w-5 items-center justify-center rounded-[5px] bg-surface-base pt-px text-xs font-medium text-ink-gray-8 shadow-sm"
							>
								{{ filters.length }}
							</span>
						</template>
					</Button>
					<Tooltip v-if="filters.length" text="Clear all filters">
						<div>
							<Button class="rounded-s-none border-s" @click.stop="clearFilters()">
								<template #icon>
									<X class="size-4" stroke-width="1.5" />
								</template>
							</Button>
						</div>
					</Tooltip>
				</div>
			</slot>
		</template>

		<template #default>
			<div
				:class="panelWidth"
				class="rounded-lg border border-outline-gray-1 bg-surface-base shadow-xl"
			>
				<div class="relative overflow-clip rounded-[inherit]">
					<Transition :name="direction === 'forward' ? 'slide-forward' : 'slide-back'">
						<div :key="step">
							<!-- Step: overview — the active conditions -->
							<template v-if="step === 'overview'">
								<div
									ref="overviewHeader"
									tabindex="-1"
									class="flex h-9 items-center border-b border-outline-gray-1 p-2 ps-3 outline-none"
									@vue:mounted="focusOverview"
								>
									<span class="text-base font-medium text-ink-gray-8">
										{{ headerLabel }}
									</span>
								</div>
								<div>
									<div class="p-1.5">
										<div
											v-for="filter in filters"
											:key="filter.id"
											class="group flex h-8 w-full items-center gap-2 rounded pl-0 pr-1.5 hover:bg-surface-gray-2"
										>
											<!-- A raw button, not frappe-ui's: the row is two differently
											     typed halves, which `label` cannot carry. -->
											<button
												class="flex h-full min-w-0 flex-1 items-center gap-1.5 rounded ps-1.5 text-start"
												@click="editFilter(filter)"
											>
												<component
													:is="columnIcon(filter.column)"
													class="size-4 shrink-0 text-ink-gray-5"
													stroke-width="1.5"
												/>
												<span
													class="truncate text-base-medium text-ink-gray-8"
												>
													{{ summaryParts(filter).label }}
												</span>
												<span class="shrink-0 text-base text-ink-gray-4"
													>·</span
												>
												<span
													:title="summaryParts(filter).value"
													class="min-w-0 flex-1 truncate text-base text-ink-gray-6"
												>
													{{ summaryParts(filter).value }}
												</span>
											</button>
											<div class="flex shrink-0 items-center gap-1">
												<Button
													variant="ghost"
													tooltip="Replace filter"
													:class="revealOnRowActivity"
													@click="replaceFilter(filter)"
												>
													<template #icon>
														<ArrowLeftRight
															class="size-4"
															stroke-width="1.5"
														/>
													</template>
												</Button>
												<Button
													variant="ghost"
													tooltip="Remove filter"
													:class="revealOnRowActivity"
													@click="removeFilter(filter.id)"
												>
													<template #icon>
														<X class="size-4" stroke-width="1.5" />
													</template>
												</Button>
											</div>
										</div>
									</div>
									<div
										class="flex items-center justify-between border-t border-outline-gray-1 px-1 py-1.5"
									>
										<Button
											variant="ghost"
											size="sm"
											label="Add filter"
											tooltip="Add filter (A)"
											class="!text-ink-gray-5"
											@click="addNewFilter()"
										>
											<template #prefix>
												<Plus class="size-4" stroke-width="1.5" />
											</template>
										</Button>
										<Button
											variant="ghost"
											size="sm"
											label="Clear all"
											class="!text-ink-gray-5"
											@click="clearFilters()"
										>
											<template #prefix>
												<Trash2 class="size-4" stroke-width="1.5" />
											</template>
										</Button>
									</div>
								</div>
							</template>

							<!-- Step: fields — choose a column -->
							<template v-else-if="step === 'fields'">
								<div
									v-if="canGoBack"
									class="flex h-9 items-center border-b border-outline-gray-1 ps-1"
								>
									<Button
										variant="ghost"
										:label="headerLabel"
										class="!justify-start truncate font-medium text-ink-gray-8 hover:bg-transparent"
										@click="goBack()"
									>
										<template #prefix>
											<ChevronLeft class="size-4" stroke-width="1.5" />
										</template>
									</Button>
								</div>
								<ProtoFilterFieldList
									:columns="columns"
									:placeholder="canGoBack ? 'Search columns...' : 'Add filter...'"
									:show-shortcut-hint="!filters.length"
									@select="selectColumn"
									@back="goBack"
								/>
							</template>

							<!-- Step: value — operator + value, with its own header -->
							<ProtoFilterValueEditor
								v-else-if="step === 'value' && selectedColumn"
								:key="editSession"
								:column="selectedColumn"
								:filter="editingFilter"
								:values-provider="valuesProvider(selectedColumn)"
								@apply="applyFilter"
								@clear="clearCurrentFilter"
								@back="goBack"
								@done="step = 'overview'"
							/>
						</div>
					</Transition>
				</div>
			</div>
		</template>
	</Popover>
</template>

<style scoped>
/* Panels are transparent at rest so they never paint over the popover border;
   they only need their own background while two of them overlap mid-swipe. */
.slide-forward-enter-active,
.slide-forward-leave-active,
.slide-back-enter-active,
.slide-back-leave-active {
	background-color: var(--surface-base);
	transition:
		transform 250ms cubic-bezier(0.2, 0, 0, 1),
		opacity 250ms cubic-bezier(0.2, 0, 0, 1);
}

/* The outgoing panel leaves the flow so both panels can swipe at once. The
   incoming forward panel stacks above it, like a navigation push. */
.slide-forward-leave-active,
.slide-back-leave-active {
	position: absolute;
	top: 0;
	inset-inline: 0;
}

.slide-forward-enter-active {
	position: relative;
	z-index: 1;
}

.slide-forward-enter-from,
.slide-back-leave-to {
	transform: translateX(100%);
}

.slide-forward-leave-to,
.slide-back-enter-from {
	transform: translateX(-25%);
	opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
	.slide-forward-enter-active,
	.slide-forward-leave-active,
	.slide-back-enter-active,
	.slide-back-leave-active {
		transition-duration: 0s;
	}
}
</style>
