<script setup lang="ts">
import { computed, ref } from 'vue'
import Toggle from '../../components/Toggle.vue'
import VisibilitySelector from '../../components/VisibilitySelector.vue'
import { copyToClipboard } from '../../helpers'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { __ } from '../../translation'
import { Chart } from '../chart'
import { useChartShare } from './chart_share'

const props = defineProps<{ chart: Chart }>()
const show = defineModel()

const chart = props.chart

const onPublicDashboard = ref(false)
const { visibility, visibleToRoles, runAsOwner, isPublic, canMoveRunAsOwner, hasChanged } =
	useChartShare(chart, onPublicDashboard)

const shareLink = computed(() => chart.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="300" frameborder="0"></iframe>`
})

// A chart's own level is half of how far it reaches. The other half is the
// dashboards it sits on: their readers get read on every chart on the grid, so
// a Private chart under a published dashboard is published by it — which is
// exactly the state `run_public_charts_as_owner` leaves behind, and the state
// this dialog is the only way out of. The server computes it; the dialog asks
// once, when it opens against a loaded document.
const publishedByDashboard = ref<string | null>(null)
chart.doc.name &&
	chart
		.call('published_reach')
		.then((reach: { published_by_dashboard: string | null; on_public_dashboard: boolean }) => {
			publishedByDashboard.value = reach?.published_by_dashboard || null
			onPublicDashboard.value = Boolean(reach?.on_public_dashboard)
		})
		.catch(() => {})

// Every level above Private reaches a population nobody named one at a time —
// the same boundary the server publishes by. `Roles` with no role named reaches
// nobody yet.
const wideVisibility = computed(
	() =>
		visibility.value === 'Public' ||
		visibility.value === 'Everyone' ||
		(visibility.value === 'Roles' && visibleToRoles.value.length > 0),
)
const exposesOwnerRows = computed(
	() => (wideVisibility.value || Boolean(publishedByDashboard.value)) && runAsOwner.value,
)

function saveChanges() {
	if (exposesOwnerRows.value) {
		confirmDialog({
			title: __("Show everyone the rows this chart's owner can see?"),
			message: publishedByDashboard.value
				? __(
						'This chart is on the published dashboard {0}. Running it as its owner makes everyone who can open that dashboard see the rows its owner can see, including rows their own permissions would hide.',
						publishedByDashboard.value,
				  )
				: __(
						'Running this chart as its owner makes everyone who can open it see the rows its owner can see, including rows their own permissions would hide. Use it only for numbers you would publish.',
				  ),
			theme: 'red',
			primaryActionLabel: __('Yes, run as owner'),
			onSuccess: applyChanges,
		})
		return
	}
	applyChanges()
}

function applyChanges() {
	chart.doc.visibility = visibility.value
	chart.doc.visible_to_roles = visibleToRoles.value.map((role) => ({ role }))
	chart.doc.run_as_owner = runAsOwner.value
	show.value = false
}
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="__('Share Chart')"
		:actions="[
			{
				label: __('Done'),
				variant: 'solid',
				disabled: !hasChanged,
				onClick: saveChanges,
			},
		]"
	>
		<template #default>
			<div class="flex flex-col gap-4 text-base">
				<VisibilitySelector v-model:visibility="visibility" v-model:roles="visibleToRoles">
					<template #actions>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button icon="lucide-link-2" @click="copyToClipboard(shareLink)">
							</Button>
						</Tooltip>
						<Tooltip text="Copy iFrame" :hoverDelay="0.1">
							<Button icon="lucide-code" @click="copyToClipboard(iFrameLink)">
							</Button>
						</Tooltip>
					</template>
				</VisibilitySelector>

				<div class="flex flex-col gap-2">
					<div class="flex items-center justify-between gap-2">
						<span class="text-sm text-ink-gray-5">
							{{ __('Run as owner') }}
						</span>
						<Toggle v-model="runAsOwner" :disabled="!canMoveRunAsOwner" />
					</div>
					<p v-if="isPublic || !exposesOwnerRows" class="text-sm text-ink-gray-5">
						{{
							runAsOwner
								? __(
										"Every reader sees the rows this chart's owner can see, and nothing behind the chart.",
								  )
								: isPublic
								  ? __(
											'Guests have no permissions of their own, so a public link shows them nothing until the chart runs as its owner.',
								    )
								  : __('Each reader sees the rows their own permissions allow.')
						}}
					</p>
					<p v-else class="text-sm text-ink-red-5">
						{{
							publishedByDashboard
								? __(
										"This chart is on the published dashboard {0}, so everyone who can open it will see the rows this chart's owner can see.",
										publishedByDashboard,
								  )
								: __(
										"Everyone will see the rows this chart's owner can see, including rows their own permissions would hide.",
								  )
						}}
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
