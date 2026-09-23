// The app an island mounts, made this app's. It runs after desk's
// `SetVueGlobals`, so the `__` installed here is the one templates get.

import type { App } from 'vue'
import { registerGlobalComponents } from '../globals'
import { installTranslate } from '../translation'

export function configureIsland(app: App) {
	installTranslate(app)
	registerGlobalComponents(app)
}
