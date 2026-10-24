// Only the SPA provides these. They are kept out of `globals.ts` because
// `$socket` opens a socket. Islands import `globals.ts`, so they would bundle
// socket.io-client and open a second connection beside the host page's own.

import { App } from 'vue'
import dayjs from './helpers/dayjs.ts'
import { getSocket } from './socket.ts'

export function registerControllers(app: App) {
	app.provide('$dayjs', dayjs)
	app.provide('$socket', getSocket())
}
