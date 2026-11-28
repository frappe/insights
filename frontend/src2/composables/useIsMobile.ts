import { breakpointsTailwind, useBreakpoints } from '@vueuse/core'
import { effectScope, type Ref } from 'vue'

let isMobile: Ref<boolean> | undefined

// The phone layout: below Tailwind's `sm`, the width where `max-sm:` classes
// apply. For the places that render a different component, not just restyle.
// One listener for the app, in its own scope, so it outlives the component
// that asked first.
export function useIsMobile() {
	return (isMobile ??= effectScope(true).run(() =>
		useBreakpoints(breakpointsTailwind).smaller('sm'),
	)!)
}
