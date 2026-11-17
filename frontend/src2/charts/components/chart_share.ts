import { computed, Ref, ref, watch } from 'vue'
import { InsightsChartv3, Visibility } from '../../types/workbook.types'

/**
 * The share dialog's own copy of a chart's visibility, roles and Run as owner.
 *
 * It starts from the saved document. Switching to Public checks Run as owner. A
 * chart saved as Public keeps its saved value: `run_public_charts_as_owner`
 * leaves a public chart unchecked when it cannot tell whose rows the chart
 * showed, and the owner decides here.
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

	// Mirrors the server. Only a user it allows can change the saved value
	// (`may_move_run_as_owner`), and nobody can uncheck it at Public or on a
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
