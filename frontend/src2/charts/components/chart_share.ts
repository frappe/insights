import { computed, Ref, ref, watch } from 'vue'
import { InsightsChartv3, Visibility } from '../../types/workbook.types'

/**
 * The share dialog's own copy of a chart's level, roles and Run as owner box.
 *
 * Seeded from the stored row. The Public level ticks the box on the move to it,
 * never on a row that already holds another state: `run_public_charts_as_owner`
 * leaves a public chart unticked where it cannot know whose rows the base served,
 * and this dialog is where its owner decides.
 */
export function useChartShare(
	chart: {
		doc: Pick<
			InsightsChartv3,
			'visibility' | 'visible_to_roles' | 'run_as_owner' | 'can_move_run_as_owner'
		>
	},
	onPublicDashboard: Ref<boolean> = ref(false),
) {
	// the field is a check, so it arrives as 0 or 1
	const savedRunAsOwner = () => Boolean(chart.doc.run_as_owner)
	const savedRoles = () => (chart.doc.visible_to_roles || []).map((r) => r.role)

	const visibility = ref<Visibility>(chart.doc.visibility || 'Private')
	const visibleToRoles = ref(savedRoles())
	const runAsOwner = ref(savedRunAsOwner())

	const isPublic = computed(() => visibility.value === 'Public')

	// a guest has no permissions of their own, so the Public level runs as the owner
	watch(isPublic, (published) => {
		if (published) runAsOwner.value = true
	})

	// Only what the server admits: whoever it says may move the box from where
	// it is saved (`may_move_run_as_owner`), and never off at Public or on a
	// Public dashboard (`validate_run_as_owner`).
	const canMoveRunAsOwner = computed(
		() =>
			Boolean(chart.doc.can_move_run_as_owner) &&
			!((isPublic.value || onPublicDashboard.value) && runAsOwner.value),
	)

	const hasChanged = computed(
		() =>
			JSON.stringify([visibility.value, visibleToRoles.value, runAsOwner.value]) !==
			JSON.stringify([chart.doc.visibility || 'Private', savedRoles(), savedRunAsOwner()]),
	)

	return { visibility, visibleToRoles, runAsOwner, isPublic, canMoveRunAsOwner, hasChanged }
}
