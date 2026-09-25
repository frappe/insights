// Sets up the Vue app an island mounts. It runs after desk's `SetVueGlobals`,
// so templates get the `__` installed here, not desk's.

import type { App } from 'vue'
import { registerGlobalComponents } from '../globals'
import { installTranslate } from '../translation'

export function configureIsland(app: App) {
	installTranslate(app)
	registerGlobalComponents(app)
}
