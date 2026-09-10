// The injections only the SPA makes. Apart from `globals.ts` because one of
// them opens a socket: an island that imported the component registrations
// would bundle socket.io-client and open a second connection beside the one its
// host page already holds.

import { App } from 'vue'
import dayjs from './helpers/dayjs.ts'
import { getSocket } from './socket.ts'

export function registerControllers(app: App) {
	app.provide('$dayjs', dayjs)
	app.provide('$socket', getSocket())
}
