<script setup lang="ts">
import { Button, FormControl, Popover, usePortalTarget } from 'frappe-ui'
import { ChevronLeft, ChevronRight, Layers, Rows3, Search } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'
import { __ } from '../../translation'
import { columnLabel, type DrillDimension } from './drill_stack'
import type { ClickPoint } from './segment_click'

// What a segment click offers, before anything is loaded.
//
// Two items, and the second one absorbs the dimension picker so a breakdown is
// two clicks from the chart. Nothing is fetched until the reader has said which
// they want — the candidates rode in with the rows the chart already has.
//
// The menu opens where the reader pointed, which is why it hangs off a zero-size
// anchor placed at the click rather than off a control on the page: there is no
// control, only a bar. The anchor carries viewport coordinates, so it is
// teleported out of the chart — `position: fixed` is measured against the nearest
// transformed ancestor, and the builder's grid moves its cards with `translate3d`,
// which would put the menu the width of a card away from the click.
//
// It goes to the same place the popover's own content portals to, and not to the
// body. In the SPA the two are the same element. In a desk island they are not:
// the island renders inside a shadow root and names a portal target in it, so an
// anchor sent to the document body leaves the tree the island's stylesheet
// reaches. It loses `position: fixed` there and lands wherever the desk page's
// flow puts it, which is where the menu then opens.
const props = defineProps<{
	point: ClickPoint
	/** the columns this segment can still be split by, already ordered */
	dimensions: DrillDimension[]
}>()

const emit = defineEmits<{
	records: []
	// eslint-disable-next-line no-unused-vars
	breakdown: [dimension: DrillDimension]
	close: []
}>()

const pane = ref<'actions' | 'dimensions'>('actions')
const search = ref('')
const searchInput = ref<HTMLElement>()

const matches = computed(() => {
	const term = search.value.trim().toLowerCase()
	if (!term) return props.dimensions
	return props.dimensions.filter(
		(dimension) =>
			dimension.name.toLowerCase().includes(term) ||
			columnLabel(dimension.name).toLowerCase().includes(term),
	)
})

// undefined outside an island, which is Teleport's own default target anyway
const portalTarget = usePortalTarget()

// A row is a ghost Button and not frappe-ui's ItemListRow, which is the shell a
// menu row is made of. ItemListRow's utilities reach this menu on no surface I
// could find — the same panel styles its Button, its FormControl and its own
// shell — so the row it draws lands unstyled. Left as a Button until that is
// understood; a row that has to look right in an island is not the place to
// find out.
const rowClass = 'w-full !justify-start'

function openDimensions() {
	pane.value = 'dimensions'
	// a long list is the case the search exists for, so the reader lands in it
	nextTick(() => searchInput.value?.querySelector('input')?.focus())
}
</script>

<template>
	<Teleport :to="portalTarget ?? 'body'">
		<Popover
			:open="true"
			side="bottom"
			align="start"
			@update:open="(open: boolean) => !open && emit('close')"
		>
			<template #trigger>
				<div
					class="pointer-events-none fixed h-0 w-0"
					:style="{ left: `${props.point.x}px`, top: `${props.point.y}px` }"
				/>
			</template>

			<div class="w-56 p-1.5">
				<div v-if="pane === 'actions'" class="flex flex-col gap-0.5">
					<Button variant="ghost" :class="rowClass" @click="emit('records')">
						<template #prefix>
							<Rows3 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
						<span class="truncate">{{ __('View records') }}</span>
					</Button>
					<!-- A segment that pins every dimension the query has left cannot be
					     split any further, and the records are the only way on. -->
					<Button
						v-if="props.dimensions.length"
						variant="ghost"
						:class="rowClass"
						@click="openDimensions"
					>
						<template #prefix>
							<Layers class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
						<span class="truncate">{{ __('Break down by') }}</span>
						<template #suffix>
							<ChevronRight class="h-4 w-4 text-ink-gray-5" stroke-width="1.5" />
						</template>
					</Button>
				</div>

				<div v-else class="flex flex-col gap-1.5">
					<div class="flex items-center gap-1">
						<Button variant="ghost" @click="pane = 'actions'">
							<template #icon>
								<ChevronLeft class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
						<div ref="searchInput" class="flex-1">
							<FormControl
								type="text"
								size="sm"
								v-model="search"
								:placeholder="__('Search')"
							>
								<template #prefix>
									<Search class="h-4 w-4 text-ink-gray-5" stroke-width="1.5" />
								</template>
							</FormControl>
						</div>
					</div>

					<div class="flex max-h-64 flex-col gap-0.5 overflow-y-auto">
						<Button
							v-for="dimension in matches"
							:key="dimension.name"
							variant="ghost"
							:class="rowClass"
							@click="emit('breakdown', dimension)"
						>
							<span class="truncate">{{ columnLabel(dimension.name) }}</span>
						</Button>
						<p v-if="!matches.length" class="px-2 py-1.5 text-base text-ink-gray-5">
							{{ __('No matching columns') }}
						</p>
					</div>
				</div>
			</div>
		</Popover>
	</Teleport>
</template>
