import { io } from 'socket.io-client'

export function initSocket() {
	let socketio_port = window.socketio_port || 9000
	let host = window.location.hostname
	let siteName = import.meta.env.DEV ? host : window.site_name
	let port = window.location.port ? `:${socketio_port}` : ''
	let protocol = port ? 'http' : 'https'
	let url = `${protocol}://${host}${port}/${siteName}`

	let socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}
