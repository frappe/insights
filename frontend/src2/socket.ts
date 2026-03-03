import { io, Socket } from 'socket.io-client'

let socket: Socket

declare global {
	interface Window {
		site_name: string
		socketio_port: number
	}
}

export function getSocket() {
	if (socket) {
		return socket
	}

	let socket_port = window.socketio_port || 9000
	let host = window.location.hostname
	let siteName = import.meta.env.DEV ? host : window.site_name
	let port = window.location.port ? `:${socket_port}` : ''
	let protocol = port ? 'http' : 'https'
	let url = `${protocol}://${host}${port}/${siteName}`

	socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}
