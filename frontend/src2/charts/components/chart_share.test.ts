import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'
import { useChartShare } from './chart_share'

// `ChartBuilder` mounts the dialog with `v-if` after `loadDoc` fills
// `useChart().doc`, so these tests start from a loaded chart.

function shareOf(doc: Record<string, any>, onPublicDashboard = false) {
	return useChartShare(
		{ doc: { visibility: 'Private', can_move_run_as_owner: true, ...doc } as any },
		ref(onPublicDashboard),
	)
}

describe('the Run as owner box in the share dialog', () => {
	// @feature permissions.chart-run-as-owner shared.rows-are-the-owners
	it('shows a public chart the box the row holds and leaves Done off until something moves', () => {
		// the patch `run_public_charts_as_owner` leaves this when the publisher is not the owner
		const share = shareOf({ visibility: 'Public', run_as_owner: 0 })

		expect(share.runAsOwner.value).toBe(false)
		expect(share.canMoveRunAsOwner.value).toBe(true)
		expect(share.hasChanged.value).toBe(false)
	})

	// @feature permissions.chart-run-as-owner shared.rows-are-the-owners
	it('ticks the box when the visibility level moves to Public, then refuses the untick as the server does', async () => {
		const share = shareOf({ visibility: 'Everyone', run_as_owner: 0 })

		share.visibility.value = 'Public'
		await nextTick()

		expect(share.runAsOwner.value).toBe(true)
		expect(share.canMoveRunAsOwner.value).toBe(false)
	})

	// @feature permissions.chart-run-as-owner
	it('leaves the box to whoever the server says may move it', () => {
		const share = shareOf({ run_as_owner: 1, can_move_run_as_owner: false })

		expect(share.runAsOwner.value).toBe(true)
		expect(share.canMoveRunAsOwner.value).toBe(false)
	})

	// @feature permissions.chart-run-as-owner shared.chart-on-public-dashboard
	it('keeps the box on for a chart on a public dashboard, as the server does', () => {
		const share = shareOf({ visibility: 'Private', run_as_owner: 1 }, true)

		expect(share.canMoveRunAsOwner.value).toBe(false)
	})
})
