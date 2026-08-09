// The injections only the SPA makes. Apart from `globals.ts` because one of
// them opens a socket: an island that imported the component registrations
// would carry socket.io-client, and the page's import map has no entry for it.

import { App } from 'vue'
import dayjs from './helpers/dayjs.ts'
import { createToast } from './helpers/toasts'
import { getSocket } from './socket.ts'

export function registerControllers(app: App) {
	app.provide('$dayjs', dayjs)
	app.provide('$notify', createToast)
	app.provide('$socket', getSocket())
}
