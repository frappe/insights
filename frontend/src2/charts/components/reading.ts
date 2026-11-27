// frappe-ui keeps a plot's tooltip, its reading, open until the pointer leaves
// the plot, and offers no other way to close it. A leave is what closes it here.
export function closeReadings(box: Element | null | undefined) {
	box
		?.querySelectorAll('[data-slot="chart-plot"] [role="img"]')
		.forEach((plot) => plot.dispatchEvent(new PointerEvent('pointerleave')))
}

// A finger never leaves a plot the way a mouse does, so a touch outside a chart
// closes its reading. One listener for every chart on the page.
let listening = false
export function closeReadingsOnTouchOutside() {
	if (listening || typeof document === 'undefined') return
	listening = true
	document.addEventListener(
		'pointerdown',
		(event) => {
			if (event.pointerType !== 'touch') return
			const touched = (event.target as Element).closest?.('[data-chart-body]')
			document
				.querySelectorAll('[data-chart-body]')
				.forEach((chart) => chart !== touched && closeReadings(chart))
		},
		{ capture: true, passive: true },
	)
}
