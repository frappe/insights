<script setup lang="ts">
// The popover's inside: one input, and under it one list per stage. reka's
// combobox owns the highlight and the arrow keys; this file owns what a pick
// means.
import { Badge, KeyboardShortcut, Tooltip } from 'frappe-ui'
import { Delete, Plus, Search } from 'lucide-vue-next'
import { ComboboxInput, ComboboxRoot } from 'reka-ui'
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { __ } from '../../translation'
import type { FilterOperator, FilterValue, QueryResultColumn } from '../../types/query.types'
import {
	calendarOf,
	columnIcon,
	DATE_PRESETS,
	formatDate,
	isMulti,
	kindOf,
	NUMBER_PAIRS,
	NUMBER_QUICK,
	numberPreview,
	operatorRows,
	parseDatePhrase,
	parseNumber,
	parseSpan,
	pathOf,
	RELATIVE_DIRECTIONS,
	RELATIVE_ROW,
	spanDates,
	splitPair,
	summaryParts,
	textRule,
	unitRows,
	type Filter,
	type ListItem,
	type OperatorDef,
	type SpanDirection,
	type Stage,
} from './filter_picker'
import FilterPickerCalendar from './FilterPickerCalendar.vue'
import FilterPickerList from './FilterPickerList.vue'

// the root is reka's combobox, and an attribute that fell through onto it would
// overwrite the model this file hands it
defineOptions({ inheritAttrs: false })

const props = defineProps<{
	columns: QueryResultColumn[]
	valuesProvider: (column: QueryResultColumn) => (search: string) => Promise<string[]>
	column?: QueryResultColumn
	filters: Filter[]
	initial?: Filter
}>()
const emit = defineEmits<{
	commit: [filter: Filter, replacing?: Filter]
	remove: [filter: Filter]
	close: []
}>()

type Draft = { operator: FilterOperator; value: FilterValue }

// --- state -----------------------------------------------------------------

const stage = ref<Stage>('column')
const history = ref<Stage[]>([])
const column = ref<QueryResultColumn | undefined>(props.column)
const op = ref<OperatorDef | undefined>()
const search = ref('')
const editing = ref<Filter | undefined>()

const picked = ref<string[]>([])
/** the values already ticked when the multi stage opened, in tick order */
const sticky = ref<string[]>([])
const relative = reactive<{ direction: SpanDirection; includeCurrent: boolean }>({
	direction: 'last',
	includeCurrent: false,
})

const kind = computed(() => (column.value ? kindOf(column.value.type) : undefined))
const multi = computed(
	() => stage.value === 'value' && kind.value === 'text' && isMulti('text', op.value),
)
const between = computed(() => op.value?.operator === 'between')
/** the calendar an operator opens sits under the list, not inside a row */
const calendar = computed(() =>
	stage.value === 'value' && kind.value === 'date' && op.value ? calendarOf(op.value) : undefined,
)
/** the count the relative stages read off the input; an empty input is 1 */
const relCount = computed(() => parseNumber(search.value) ?? 1)
const relativeForm = computed(() => ({
	direction: relative.direction,
	count: relCount.value,
	unit: 'day' as const,
	includeCurrent: relative.includeCurrent,
}))

/** reka holds the ticks while the text `=` / `≠` stage is up, nothing otherwise */
const NONE: string[] = []
const comboModel = computed(() => (multi.value ? picked.value : NONE))
function onComboModel(value: unknown) {
	if (multi.value) picked.value = (value as string[]) || []
}

function firstStage(): Stage {
	if (props.column) return 'operator'
	return props.filters.length ? 'overview' : 'column'
}

function clearValue() {
	picked.value = []
	sticky.value = []
	relative.direction = 'last'
	relative.includeCurrent = false
}

function go(next: Stage) {
	history.value.push(stage.value)
	stage.value = next
	search.value = ''
}

function reset() {
	history.value = []
	column.value = props.column
	op.value = undefined
	editing.value = undefined
	search.value = ''
	clearValue()
	stage.value = firstStage()
}

function load(filter: Filter) {
	reset()
	const path = pathOf(filter)
	editing.value = filter
	column.value = path.column
	op.value = path.op
	picked.value = path.picked
	sticky.value = [...path.picked]
	search.value = multi.value ? '' : path.text
	history.value = props.column ? ['operator'] : ['overview', 'column', 'operator']
	stage.value = 'value'
	if (path.relative) {
		relative.direction = path.relative.direction
		relative.includeCurrent = path.relative.includeCurrent
		history.value.push('value', 'relative')
		stage.value = 'unit'
	}
}

if (props.initial) load(props.initial)
else reset()

// --- distinct values -------------------------------------------------------

const distinct = ref<string[]>([])
const fetching = ref(false)
let request = 0

watch(
	[() => column.value?.name, search, multi],
	async ([, text, isMultiStage]) => {
		if (!isMultiStage || !column.value) {
			distinct.value = []
			return
		}
		const id = ++request
		fetching.value = true
		const values = await props
			.valuesProvider(column.value)(text as string)
			.catch(() => [])
		if (id !== request) return
		// reka's ComboboxItem throws on an empty value
		distinct.value = values.filter(Boolean)
		fetching.value = false
	},
	{ immediate: true },
)

// --- typed text ------------------------------------------------------------

/** The rule the typed text spells, where the stage has a place for one. */
const typed = computed<(Draft & { label: string; note?: string }) | undefined>(() => {
	const text = search.value.trim()
	if (stage.value !== 'value' || !text || !op.value) return undefined

	if (kind.value === 'text') {
		if (multi.value) return undefined
		return { operator: op.value.operator, value: text, label: __('Use “{0}”', text) }
	}

	if (kind.value === 'number') {
		if (between.value) {
			const pair = splitPair(text)
			const from = pair && parseNumber(pair[0])
			const to = pair && parseNumber(pair[1])
			if (from === undefined || to === undefined) return undefined
			const range: [number, number] = [from, to]
			return { operator: 'between', value: range, label: numberPreview(op.value, range) }
		}
		const value = parseNumber(text)
		if (value === undefined) return undefined
		return { operator: op.value.operator, value, label: numberPreview(op.value, value) }
	}

	if (kind.value !== 'date') return undefined

	if (!calendar.value) {
		const span = parseSpan(text)
		if (!span || DATE_PRESETS.some((p) => p.label.toLowerCase() === text.toLowerCase()))
			return undefined
		return {
			operator: 'within',
			value: { span },
			label: __('Use “{0}”', text),
			note: spanDates(span),
		}
	}

	const phrase = parseDatePhrase(text)
	if (!phrase) return undefined
	if (calendar.value === 'range') {
		if (phrase.operator !== 'between') return undefined
		const [from, to] = phrase.value as string[]
		return { ...phrase, label: `${__('between')} ${formatDate(from, to)}` }
	}
	if (phrase.operator !== '=') return undefined
	const day = String(phrase.value)
	return {
		operator: op.value.operator,
		value: day,
		label: `${op.value.sign} ${formatDate(day)}`,
	}
})

// --- the draft the value stage holds ---------------------------------------

const draft = computed<Draft | undefined>(() => {
	if (stage.value !== 'value' || !op.value) return undefined
	if (kind.value === 'text' && multi.value)
		return picked.value.length ? textRule(op.value, picked.value) : undefined
	if (typed.value) return { operator: typed.value.operator, value: typed.value.value }
	return undefined
})

// --- rows ------------------------------------------------------------------

const q = computed(() => search.value.trim().toLowerCase())
const matches = (label: string) => !q.value || label.toLowerCase().includes(q.value)

const rows = computed<ListItem[]>(() => {
	if (stage.value === 'overview') {
		const applied = props.filters
			.map((filter, index) => ({ filter, index }))
			.filter(({ filter }) => matches(summaryParts(filter).label))
			.map(({ filter, index }) => ({
				key: `filter:${index}`,
				...summaryParts(filter),
				icon: columnIcon(filter.column),
				removable: true,
				filter,
			}))
		// the rows already in the list, then Add filter under a divider
		return [
			...applied,
			{ key: 'add', label: __('Add filter'), icon: Plus, separated: applied.length > 0 },
		]
	}

	if (stage.value === 'column') {
		return props.columns
			.filter((c) => matches(c.name))
			.map((c) => ({ key: c.name, label: c.name, icon: columnIcon(c) }))
	}

	if (stage.value === 'operator') {
		// a row reads as its word, the sign beside it
		return operatorRows(kind.value!)
			.filter((o) => matches(o.sign) || matches(o.word))
			.map((o) => ({
				key: o.operator,
				label: o.word,
				note: o.sign === o.word ? undefined : o.sign,
			}))
	}

	if (stage.value === 'relative') {
		return RELATIVE_DIRECTIONS.filter((d) => matches(d.label)).map((d) => ({
			key: `dir:${d.key}`,
			label: d.label,
		}))
	}

	if (stage.value === 'unit') {
		const form = relativeForm.value
		// a count in the input is the count, not a filter over the unit rows
		const typing = search.value.trim() && parseNumber(search.value) === undefined
		const units = unitRows(form)
			.filter((row) => !typing || matches(row.label))
			.map((row) => ({
				key: `span:${row.span}`,
				label: row.label,
				note: spanDates(row.span),
			}))
		if (form.direction === 'current') return units
		return [
			...units,
			{
				key: 'include',
				label: __('Include current period'),
				checked: relative.includeCurrent,
			},
		]
	}

	if (multi.value) {
		const top = sticky.value.filter((v) => matches(v))
		const rest = distinct.value.filter((v) => !top.includes(v))
		return [...top, ...rest].map((v) => ({
			key: `v:${v}`,
			label: v,
			tick: true,
			checked: picked.value.includes(v),
		}))
	}

	const use: ListItem[] = typed.value
		? [{ key: 'use', label: typed.value.label, note: typed.value.note }]
		: []

	if (kind.value === 'text') return use

	if (kind.value === 'number') {
		if (search.value.trim()) return use
		return between.value
			? NUMBER_PAIRS.map((pair) => ({
					key: `pair:${pair[0]}:${pair[1]}`,
					label: numberPreview(op.value!, pair),
			  }))
			: NUMBER_QUICK.map((v) => ({
					key: `n:${v}`,
					label: numberPreview(op.value!, v),
			  }))
	}

	// dates: the input and the highlighted grid already read the draft
	if (calendar.value) return []
	const presets = DATE_PRESETS.filter((p) => matches(p.label)).map((p) => ({
		key: `span:${p.span}`,
		label: p.label,
		note: spanDates(p.span),
	}))
	const relativeRow: ListItem[] = matches(RELATIVE_ROW.label)
		? [{ key: RELATIVE_ROW.key, label: RELATIVE_ROW.label }]
		: []
	return [...use, ...presets, ...relativeRow]
})

const emptyText = computed(() => {
	if (stage.value === 'column') return __('No columns found')
	if (stage.value === 'operator') return __('No operators found')
	if (stage.value === 'relative' || stage.value === 'unit') return __('Nothing matches')
	if (multi.value) return fetching.value ? '' : __('No values found')
	if (kind.value === 'text') return ''
	if (kind.value === 'number') return ''
	if (kind.value === 'date' && calendar.value) return ''
	if (kind.value === 'date') return __('Nothing matches')
	return ''
})

/**
 * The prompt carries what the path tokens used to. A value stage names the
 * column and the operator it is filling in, because the operator is what says
 * how much to type; the operator stage names the column alone, the operator
 * being the thing the reader is there to pick.
 */
const placeholder = computed(() => {
	const name = column.value?.name ?? ''
	const word = op.value?.word ?? ''
	if (stage.value === 'overview') return __('Filters…')
	if (stage.value === 'column') return __('Filter by…')
	if (stage.value === 'operator') return name ? `${name}…` : __('Operator…')
	if (stage.value === 'relative')
		return word
			? __('{0} Last, Next or This…', word.charAt(0).toUpperCase() + word.slice(1))
			: __('Last, Next or This…')
	if (stage.value === 'unit') {
		if (relative.direction === 'current') return __('This week, month, quarter…')
		const label = RELATIVE_DIRECTIONS.find((d) => d.key === relative.direction)!.label
		return __('{0} how many?', label)
	}
	if (!name || !op.value) return __('Type a value…')
	// numbers read by their sign, and a range keeps its example: `between 30 and
	// 50` would teach a separator the input does not parse
	if (kind.value === 'number')
		return between.value ? __('{0} between, e.g. 30 to 50', name) : `${name} ${op.value.sign} …`
	return `${name} ${word}…`
})

// --- picks -----------------------------------------------------------------

function pick(item: ListItem) {
	if (stage.value === 'overview') {
		if (item.key === 'add') go('column')
		else if (item.filter) load(item.filter)
		return
	}
	if (stage.value === 'column') {
		column.value = props.columns.find((c) => c.name === item.key)
		op.value = undefined
		clearValue()
		go('operator')
		return
	}
	if (stage.value === 'operator') {
		const chosen = operatorRows(kind.value!).find((o) => o.operator === item.key)!
		op.value = chosen
		clearValue()
		if (!chosen.needsValue) return commit({ operator: chosen.operator, value: undefined })
		go('value')
		if (multi.value) sticky.value = [...picked.value]
		return
	}
	if (stage.value === 'relative') {
		relative.direction = item.key.slice(4) as SpanDirection
		go('unit')
		return
	}
	if (stage.value === 'unit') {
		if (item.key === 'include') {
			relative.includeCurrent = !relative.includeCurrent
			// the row is redrawn with its new tick, so the highlight is put back
			highlight('include')
			return
		}
		return commit({ operator: 'within', value: { span: item.key.slice(5) } })
	}
	pickValue(item)
}

function pickValue(item: ListItem) {
	if (item.key === 'use') return commit(typed.value)

	// reka has already ticked the row by the time this runs
	if (multi.value) {
		search.value = ''
		return
	}

	if (kind.value === 'number') {
		if (item.key.startsWith('n:'))
			return commit({ operator: op.value!.operator, value: Number(item.key.slice(2)) })
		if (item.key.startsWith('pair:')) {
			const [a, b] = item.key.slice(5).split(':').map(Number)
			return commit({ operator: 'between', value: [a, b] })
		}
		return
	}

	if (item.key === RELATIVE_ROW.key) return go('relative')
	if (item.key.startsWith('span:'))
		return commit({ operator: 'within', value: { span: item.key.slice(5) } })
}

// --- commit ----------------------------------------------------------------

function commit(rule: Draft | undefined = draft.value) {
	if (!column.value || !rule) return
	emit(
		'commit',
		{
			column: column.value,
			operator: rule.operator,
			value: rule.value,
		},
		editing.value,
	)
	if (props.column) {
		editing.value = undefined
		picked.value = []
		emit('close')
		return
	}
	reset()
	stage.value = 'overview'
	focusInput()
}

// a pick left open commits when the popover closes: a tick on the multi stage,
// or the days the calendar wrote into the input
onBeforeUnmount(() => {
	if (!draft.value) return
	if (multi.value ? picked.value.length > 0 : !!calendar.value) commit()
})

// --- keys ------------------------------------------------------------------

function back() {
	const previous = history.value.pop()
	if (!previous) return
	if (stage.value === 'value') clearValue()
	if (previous === 'column') {
		op.value = undefined
		column.value = undefined
	}
	if (previous === 'overview') {
		column.value = undefined
		editing.value = undefined
	}
	stage.value = previous
	search.value = ''
	if (previous === 'operator' && op.value) highlight(op.value.operator)
}

function onKeydown(event: KeyboardEvent) {
	if (event.isComposing) return
	if (event.key === 'Backspace' && !search.value) {
		event.preventDefault()
		back()
		return
	}
	// reka answers Enter by clicking the highlighted row and marks the event
	// handled; what is left over is the stage's own commit. A multi stage never
	// commits on Enter — its rows only tick.
	if (
		event.key === 'Enter' &&
		!event.repeat &&
		!event.defaultPrevented &&
		!multi.value &&
		draft.value
	) {
		event.preventDefault()
		commit()
	}
}

/**
 * What the keys do here, named for the stage in front of the reader. Enter is
 * the row under the highlight, so it says `Apply` only where there is no row to
 * take it. `Mod+Enter` stands apart because a multi stage's Enter ticks rather
 * than commits, and Backspace leaves the text alone while there is text.
 *
 * The opening stage says nothing. Enter on the row under the highlight is the
 * only key it takes, and a list a reader is already arrowing through does not
 * need a line under it to say so.
 */
const keyHints = computed(() => {
	if (!history.value.length) return []
	const hints: { combo: string; label: string }[] = []
	if (rows.value.length) hints.push({ combo: 'Enter', label: __('Select') })
	else if (draft.value) hints.push({ combo: 'Enter', label: __('Apply') })
	if (multi.value && draft.value) hints.push({ combo: 'Mod+Enter', label: __('Apply') })
	if (history.value.length && !search.value) hints.push({ combo: 'Backspace', label: __('Back') })
	return hints
})

const isMac = navigator.platform.toUpperCase().includes('MAC')

/** Cmd+Enter commits the stage's draft before reka can read the Enter as a pick */
function onEnterCapture(event: KeyboardEvent) {
	if (event.key !== 'Enter' || event.isComposing || event.repeat) return
	if (!(isMac ? event.metaKey : event.ctrlKey)) return
	event.preventDefault()
	event.stopPropagation()
	if (draft.value) commit()
}

// --- reka's highlight ------------------------------------------------------

const comboRef = ref<any>(null)

function highlight(value: string) {
	nextTick(() => comboRef.value?.highlightItem?.(value))
}

// a stage change, a commit or a late batch of values leaves the highlight on a
// row that is gone. The nextTick here runs after any highlight() this tick
// asked for, so a restored row stands.
watch(rows, () => {
	nextTick(() => {
		const el = comboRef.value?.highlightedElement
		if (!el?.isConnected) comboRef.value?.highlightFirstItem?.()
	})
})

const inputRef = ref<any>(null)
function focusInput() {
	nextTick(() => inputRef.value?.$el?.focus({ preventScroll: true }))
}
// The opening focus is reka's: it focuses the first tabbable in the panel, which
// is the input. Taking it by hand here instead lands too early for a panel inside
// a dialog — the dialog's focus trap is released only once the popover's own
// focus scope is on the stack, and until then it pulls the caret back out.
</script>

<template>
	<ComboboxRoot
		ref="comboRef"
		:model-value="comboModel"
		:open="true"
		:multiple="multi"
		ignore-filter
		highlight-on-hover
		:reset-search-term-on-select="false"
		:reset-search-term-on-blur="false"
		class="flex w-60 flex-col overflow-hidden rounded-6 bg-surface-elevation-2 shadow-2xl ring-1 ring-black ring-opacity-5"
		@update:model-value="onComboModel"
		@keydown.capture="onEnterCapture"
	>
		<div class="flex items-center gap-2 border-b border-outline-gray-1 px-3">
			<Search v-if="!column" class="size-4 shrink-0 text-ink-gray-5" stroke-width="1.5" />
			<ComboboxInput
				ref="inputRef"
				v-model="search"
				class="min-w-20 flex-1 border-0 bg-transparent px-0 py-2 text-base text-ink-gray-8 outline-none placeholder:text-ink-gray-4 focus:ring-0"
				:placeholder="placeholder"
				@keydown="onKeydown"
			/>
			<!-- the count alone: the word "selected" is what the checkboxes below
			     already say, and the row has 240px to hold the input as well -->
			<Tooltip
				v-if="multi && picked.length"
				:text="__('{0} selected', String(picked.length))"
			>
				<Badge
					variant="subtle"
					theme="gray"
					size="sm"
					class="shrink-0"
					:label="String(picked.length)"
				/>
			</Tooltip>
			<Tooltip v-else-if="history.length && !search" :text="__('Back')">
				<Delete class="size-4 shrink-0 text-ink-gray-4" stroke-width="1.5" />
			</Tooltip>
		</div>

		<FilterPickerList
			v-if="rows.length || fetching || emptyText"
			:items="rows"
			:stage="stage"
			:loading="fetching"
			:empty="emptyText"
			@pick="pick"
			@remove="emit('remove', $event.filter!)"
		/>

		<div v-if="calendar" :class="rows.length ? 'border-t border-outline-gray-1' : ''">
			<FilterPickerCalendar :mode="calendar" :text="search" @write="search = $event" />
		</div>

		<!-- The row grows in rather than appearing: it arrives a stage after the
		     panel opened, under a list the reader is already reading. The rows of
		     the grid are what is animated, so the height comes from the line
		     itself and no number here stands for it. -->
		<Transition
			enter-active-class="transition-[grid-template-rows,opacity] duration-150 ease-out"
			enter-from-class="grid-rows-[0fr] opacity-0"
			enter-to-class="grid-rows-[1fr] opacity-100"
			leave-active-class="transition-[grid-template-rows,opacity] duration-100 ease-in"
			leave-from-class="grid-rows-[1fr] opacity-100"
			leave-to-class="grid-rows-[0fr] opacity-0"
		>
			<div v-if="keyHints.length" class="grid">
				<div class="overflow-hidden">
					<div
						class="flex items-center justify-between border-t border-outline-gray-1 px-3 py-1.5"
					>
						<span
							v-for="hint in keyHints"
							:key="hint.combo"
							class="flex items-center gap-1.5"
						>
							<!-- the component sets its own `text-sm`, so the smaller size
							     has to outrank it -->
							<KeyboardShortcut :combo="hint.combo" class="!text-xs" />
							<span class="text-xs text-ink-gray-5">{{ hint.label }}</span>
						</span>
					</div>
				</div>
			</div>
		</Transition>
	</ComboboxRoot>
</template>
