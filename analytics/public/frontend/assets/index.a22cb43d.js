var Y = (C, B, d) =>
	new Promise((p, i) => {
		var e = (c) => {
				try {
					s(d.next(c))
				} catch (f) {
					i(f)
				}
			},
			a = (c) => {
				try {
					s(d.throw(c))
				} catch (f) {
					i(f)
				}
			},
			s = (c) => (c.done ? p(c.value) : Promise.resolve(c.value).then(e, a))
		s((d = d.apply(C, B)).next())
	})
import {
	f as re,
	h as ue,
	m as ne,
	o as H,
	c as F,
	a as j,
	r as U,
	b as V,
	n as G,
	d as Z,
	F as he,
	e as $,
	t as pe,
	g as fe,
	i as oe,
	w as le,
	j as de,
	k as ye,
	l as me,
	p as I,
	q as J,
	s as ge,
} from './vendor.851992cf.js'
const ve = function () {
	const B = document.createElement('link').relList
	if (B && B.supports && B.supports('modulepreload')) return
	for (const i of document.querySelectorAll('link[rel="modulepreload"]')) p(i)
	new MutationObserver((i) => {
		for (const e of i)
			if (e.type === 'childList')
				for (const a of e.addedNodes)
					a.tagName === 'LINK' && a.rel === 'modulepreload' && p(a)
	}).observe(document, { childList: !0, subtree: !0 })
	function d(i) {
		const e = {}
		return (
			i.integrity && (e.integrity = i.integrity),
			i.referrerpolicy && (e.referrerPolicy = i.referrerpolicy),
			i.crossorigin === 'use-credentials'
				? (e.credentials = 'include')
				: i.crossorigin === 'anonymous'
				? (e.credentials = 'omit')
				: (e.credentials = 'same-origin'),
			e
		)
	}
	function p(i) {
		if (i.ep) return
		i.ep = !0
		const e = d(i)
		fetch(i.href, e)
	}
}
ve()
var z = (C, B) => {
	const d = C.__vccOpts || C
	for (const [p, i] of B) d[p] = i
	return d
}
const Q = Object.keys(re.icons),
	be = {
		props: {
			name: {
				type: String,
				required: !0,
				validator(C) {
					const B = Q.includes(C)
					return (
						B ||
							console.warn('name property for feather-icon must be one of ', Q),
						B
					)
				},
			},
			color: { type: String, default: null },
			strokeWidth: { type: Number, default: 1.5 },
		},
		render() {
			let C = re.icons[this.name]
			return ue(
				'svg',
				ne(
					C.attrs,
					{
						fill: 'none',
						stroke: 'currentColor',
						color: this.color,
						'stroke-linecap': 'round',
						'stroke-linejoin': 'round',
						'stroke-width': this.strokeWidth,
						width: null,
						height: null,
						class: [C.attrs.class],
						innerHTML: C.contents,
					},
					this.$attrs
				)
			)
		},
	},
	we = { name: 'Spinner' },
	Ce = {
		class: 'animate-spin',
		xmlns: 'http://www.w3.org/2000/svg',
		fill: 'none',
		viewBox: '0 0 24 24',
	},
	ke = j(
		'circle',
		{
			class: 'opacity-25',
			cx: '12',
			cy: '12',
			r: '10',
			stroke: 'currentColor',
			'stroke-width': '4',
		},
		null,
		-1
	),
	xe = j(
		'path',
		{
			class: 'opacity-75',
			fill: 'currentColor',
			d: 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z',
		},
		null,
		-1
	),
	_e = [ke, xe]
function Be(C, B, d, p, i, e) {
	return H(), F('svg', Ce, _e)
}
var Ae = z(we, [['render', Be]])
const Se = { name: 'LoadingIndicator', components: { Spinner: Ae } }
function Ee(C, B, d, p, i, e) {
	const a = U('Spinner')
	return H(), V(a, { class: 'w-3 h-3 mr-2 -ml-1' })
}
var Re = z(Se, [['render', Ee]])
const Ne = ['primary', 'secondary', 'danger', 'white', 'minimal'],
	Te = {
		name: 'Button',
		components: { FeatherIcon: be, LoadingIndicator: Re },
		props: {
			label: { type: String, default: null },
			appearance: {
				type: String,
				default: 'secondary',
				validator: (C) => Ne.includes(C),
			},
			disabled: { type: Boolean, default: !1 },
			iconLeft: { type: String, default: null },
			iconRight: { type: String, default: null },
			icon: { type: String, default: null },
			loading: { type: Boolean, default: !1 },
			loadingText: { type: String, default: null },
			route: {},
			link: { type: String, default: null },
		},
		computed: {
			buttonClasses() {
				let C = {
					primary:
						'bg-blue-500 hover:bg-blue-600 text-white focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
					secondary:
						'bg-gray-100 hover:bg-gray-200 text-gray-900 focus:ring-2 focus:ring-offset-2 focus:ring-gray-500',
					danger:
						'bg-red-500 hover:bg-red-400 text-white focus:ring-2 focus:ring-offset-2 focus:ring-red-500',
					white:
						'bg-white text-gray-900 border hover:bg-gray-50 focus:ring-2 focus:ring-offset-2 focus:ring-gray-400',
					minimal:
						'bg-transparent hover:bg-gray-200 active:bg-gray-200 text-gray-900',
				}
				return [
					'inline-flex items-center justify-center text-base leading-5 rounded-md transition-colors focus:outline-none',
					this.icon ? 'p-1.5' : 'px-3 py-1',
					this.isDisabled
						? 'opacity-50 cursor-not-allowed pointer-events-none'
						: '',
					C[this.appearance],
				]
			},
			isDisabled() {
				return this.disabled || this.loading
			},
		},
		methods: {
			handleClick() {
				this.route &&
					this.$router &&
					this.route &&
					this.$router.push(this.route),
					this.link && window.open(this.link, '_blank')
			},
		},
	},
	Pe = ['disabled']
function Oe(C, B, d, p, i, e) {
	const a = U('LoadingIndicator'),
		s = U('FeatherIcon')
	return (
		H(),
		F(
			'button',
			ne(C.$attrs, {
				class: e.buttonClasses,
				onClick:
					B[0] || (B[0] = (...c) => e.handleClick && e.handleClick(...c)),
				disabled: e.isDisabled,
			}),
			[
				d.loading
					? (H(),
					  V(
							a,
							{
								key: 0,
								class: G({
									'text-white': d.appearance == 'primary',
									'text-gray-600': d.appearance == 'secondary',
									'text-red-200': d.appearance == 'danger',
								}),
							},
							null,
							8,
							['class']
					  ))
					: d.iconLeft
					? (H(),
					  V(
							s,
							{
								key: 1,
								name: d.iconLeft,
								class: 'w-4 h-4 mr-1.5',
								'aria-hidden': 'true',
							},
							null,
							8,
							['name']
					  ))
					: Z('', !0),
				d.loading && d.loadingText
					? (H(), F(he, { key: 2 }, [$(pe(d.loadingText), 1)], 64))
					: d.icon
					? (H(),
					  V(
							s,
							{ key: 3, name: d.icon, class: 'w-4 h-4', 'aria-label': d.label },
							null,
							8,
							['name', 'aria-label']
					  ))
					: Z('', !0),
				j(
					'span',
					{ class: G(d.icon ? 'sr-only' : '') },
					[fe(C.$slots, 'default')],
					2
				),
				d.iconRight
					? (H(),
					  V(
							s,
							{
								key: 4,
								name: d.iconRight,
								class: 'w-4 h-4 ml-2',
								'aria-hidden': 'true',
							},
							null,
							8,
							['name']
					  ))
					: Z('', !0),
			],
			16,
			Pe
		)
	)
}
var De = z(Te, [['render', Oe]])
function ie(p, i) {
	return Y(this, arguments, function* (C, B, d = {}) {
		B || (B = {})
		let e = Object.assign(
			{
				Accept: 'application/json',
				'Content-Type': 'application/json; charset=utf-8',
				'X-Frappe-Site-Name': window.location.hostname,
			},
			d.headers || {}
		)
		window.csrf_token &&
			window.csrf_token !== '{{ csrf_token }}' &&
			(e['X-Frappe-CSRF-Token'] = window.csrf_token)
		const a = yield fetch(`/api/method/${C}`, {
			method: 'POST',
			headers: e,
			body: JSON.stringify(B),
		})
		if (a.ok) {
			const s = yield a.json()
			if (s.docs || C === 'login') return s
			if (s.exc)
				try {
					console.groupCollapsed(C),
						console.log(`method: ${C}`),
						console.log('params:', B)
					let c = JSON.parse(s.exc)
					for (let f of c) console.log(f)
					console.groupEnd()
				} catch (c) {
					console.warn('Error printing debug messages', c)
				}
			return s.message
		} else {
			let s = yield a.text(),
				c,
				f
			try {
				c = JSON.parse(s)
			} catch (h) {}
			let y = [[C, c.exc_type, c._error_message].filter(Boolean).join(' ')]
			if (c.exc) {
				f = c.exc
				try {
					;(f = JSON.parse(f)[0]), console.log(f)
				} catch (h) {}
			}
			let m = new Error(
				y.join(`
`)
			)
			throw (
				((m.exc_type = c.exc_type),
				(m.exc = f),
				(m.status = a.status),
				(m.messages = c._server_messages ? JSON.parse(c._server_messages) : []),
				(m.messages = m.messages.concat(c.message)),
				(m.messages = m.messages.map((h) => {
					try {
						return JSON.parse(h).message
					} catch (n) {
						return h
					}
				})),
				(m.messages = m.messages.filter(Boolean)),
				m.messages.length ||
					(m.messages = c._error_message
						? [c._error_message]
						: ['Internal Server Error']),
				d.onError && d.onError({ response: a, status: a.status, error: m }),
				m)
			)
		}
	})
}
function Le(C, B, d) {
	var p
	return function () {
		var i = this,
			e = arguments,
			a = function () {
				;(p = null), d || C.apply(i, e)
			},
			s = d && !p
		clearTimeout(p), (p = setTimeout(a, B)), s && C.apply(i, e)
	}
}
let M = {}
function ee(C, B, d) {
	let p = null
	if (C.cache && ((p = se(C.cache)), M[p])) return M[p]
	typeof C == 'string' && (C = { method: C, auto: !0 })
	let i = d || ie,
		e = C.debounce ? Le(s, C.debounce) : s,
		a = oe({
			data: C.initialData || null,
			previousData: null,
			loading: !1,
			fetched: !1,
			error: null,
			auto: C.auto,
			params: null,
			fetch: e,
			submit: e,
			update: c,
		})
	function s(y) {
		return Y(this, null, function* () {
			if (
				(y instanceof Event && (y = null),
				(a.params = y || C.params),
				(a.previousData = a.data ? JSON.parse(JSON.stringify(a.data)) : null),
				(a.loading = !0),
				C.onFetch && C.onFetch.call(B, a.params),
				C.validate)
			) {
				let m
				try {
					if (
						((m = yield C.validate.call(B, a.params)),
						m && typeof m == 'string')
					) {
						let h = new Error(m)
						f(h), (a.loading = !1)
						return
					}
				} catch (h) {
					f(h), (a.loading = !1)
					return
				}
			}
			try {
				let m = yield i(C.method, y || C.params)
				;(a.data = m), (a.fetched = !0), C.onSuccess && C.onSuccess.call(B, m)
			} catch (m) {
				f(m)
			}
			a.loading = !1
		})
	}
	function c({ method: y, params: m, auto: h }) {
		y && y !== C.method && (C.method = y),
			m && m !== C.params && (C.params = m),
			h !== void 0 && h !== a.auto && (a.auto = h)
	}
	function f(y) {
		console.error(y),
			a.previousData && (a.data = a.previousData),
			(a.error = y),
			C.onError && C.onError.call(B, y)
	}
	return p && !M[p] && (M[p] = a), a
}
function se(C) {
	return typeof C == 'string' && (C = [C]), JSON.stringify(C)
}
let qe = (C) => ({
	created() {
		if (this.$options.resources) {
			this._resources = oe({})
			for (let B in this.$options.resources) {
				let d = this.$options.resources[B]
				if (typeof d == 'function')
					le(
						() => d.call(this),
						(p, i) => {
							if (!(!i || JSON.stringify(p) !== JSON.stringify(i))) return
							let a = this._resources[B]
							a
								? a.update(p)
								: ((a = ee(p, this, C.getResource)), (this._resources[B] = a)),
								a.auto && a.fetch()
						},
						{ immediate: !0 }
					)
				else {
					let p = ee(d, this, C.getResource)
					;(this._resources[B] = p), p.auto && p.fetch()
				}
			}
		}
	},
	methods: {
		$refetchResource(B) {
			let d = se(B)
			M[d] && M[d].fetch()
		},
	},
	computed: {
		$resources() {
			return this._resources
		},
	},
})
var je = {
		install(C, B) {
			let d = qe(B)
			C.mixin(d)
		},
	},
	ae = { exports: {} }
/*!
 * Socket.IO v2.4.0
 * (c) 2014-2021 Guillermo Rauch
 * Released under the MIT License.
 */ ;(function (C, B) {
	;(function (d, p) {
		C.exports = p()
	})(de, function () {
		return (function (d) {
			function p(e) {
				if (i[e]) return i[e].exports
				var a = (i[e] = { exports: {}, id: e, loaded: !1 })
				return d[e].call(a.exports, a, a.exports, p), (a.loaded = !0), a.exports
			}
			var i = {}
			return (p.m = d), (p.c = i), (p.p = ''), p(0)
		})([
			function (d, p, i) {
				function e(m, h) {
					;(typeof m == 'undefined' ? 'undefined' : a(m)) === 'object' &&
						((h = m), (m = void 0)),
						(h = h || {})
					var n,
						o = s(m),
						r = o.source,
						t = o.id,
						u = o.path,
						g = y[t] && u in y[t].nsps,
						l =
							h.forceNew || h['force new connection'] || h.multiplex === !1 || g
					return (
						l ? (n = f(r, h)) : (y[t] || (y[t] = f(r, h)), (n = y[t])),
						o.query && !h.query && (h.query = o.query),
						n.socket(o.path, h)
					)
				}
				var a =
						typeof Symbol == 'function' && typeof Symbol.iterator == 'symbol'
							? function (m) {
									return typeof m
							  }
							: function (m) {
									return m &&
										typeof Symbol == 'function' &&
										m.constructor === Symbol &&
										m !== Symbol.prototype
										? 'symbol'
										: typeof m
							  },
					s = i(1),
					c = i(4),
					f = i(9)
				i(3)('socket.io-client'), (d.exports = p = e)
				var y = (p.managers = {})
				;(p.protocol = c.protocol),
					(p.connect = e),
					(p.Manager = i(9)),
					(p.Socket = i(34))
			},
			function (d, p, i) {
				function e(s, c) {
					var f = s
					;(c = c || (typeof location != 'undefined' && location)),
						s == null && (s = c.protocol + '//' + c.host),
						typeof s == 'string' &&
							(s.charAt(0) === '/' &&
								(s = s.charAt(1) === '/' ? c.protocol + s : c.host + s),
							/^(https?|wss?):\/\//.test(s) ||
								(s =
									typeof c != 'undefined'
										? c.protocol + '//' + s
										: 'https://' + s),
							(f = a(s))),
						f.port ||
							(/^(http|ws)$/.test(f.protocol)
								? (f.port = '80')
								: /^(http|ws)s$/.test(f.protocol) && (f.port = '443')),
						(f.path = f.path || '/')
					var y = f.host.indexOf(':') !== -1,
						m = y ? '[' + f.host + ']' : f.host
					return (
						(f.id = f.protocol + '://' + m + ':' + f.port),
						(f.href =
							f.protocol +
							'://' +
							m +
							(c && c.port === f.port ? '' : ':' + f.port)),
						f
					)
				}
				var a = i(2)
				i(3)('socket.io-client:url'), (d.exports = e)
			},
			function (d, p) {
				function i(c, f) {
					var y = /\/{2,9}/g,
						m = f.replace(y, '/').split('/')
					return (
						(f.substr(0, 1) != '/' && f.length !== 0) || m.splice(0, 1),
						f.substr(f.length - 1, 1) == '/' && m.splice(m.length - 1, 1),
						m
					)
				}
				function e(c, f) {
					var y = {}
					return (
						f.replace(/(?:^|&)([^&=]*)=?([^&]*)/g, function (m, h, n) {
							h && (y[h] = n)
						}),
						y
					)
				}
				var a =
						/^(?:(?![^:@]+:[^:@\/]*@)(http|https|ws|wss):\/\/)?((?:(([^:@]*)(?::([^:@]*))?)?@)?((?:[a-f0-9]{0,4}:){2,7}[a-f0-9]{0,4}|[^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/,
					s = [
						'source',
						'protocol',
						'authority',
						'userInfo',
						'user',
						'password',
						'host',
						'port',
						'relative',
						'path',
						'directory',
						'file',
						'query',
						'anchor',
					]
				d.exports = function (c) {
					var f = c,
						y = c.indexOf('['),
						m = c.indexOf(']')
					y != -1 &&
						m != -1 &&
						(c =
							c.substring(0, y) +
							c.substring(y, m).replace(/:/g, ';') +
							c.substring(m, c.length))
					for (var h = a.exec(c || ''), n = {}, o = 14; o--; )
						n[s[o]] = h[o] || ''
					return (
						y != -1 &&
							m != -1 &&
							((n.source = f),
							(n.host = n.host
								.substring(1, n.host.length - 1)
								.replace(/;/g, ':')),
							(n.authority = n.authority
								.replace('[', '')
								.replace(']', '')
								.replace(/;/g, ':')),
							(n.ipv6uri = !0)),
						(n.pathNames = i(n, n.path)),
						(n.queryKey = e(n, n.query)),
						n
					)
				}
			},
			function (d, p) {
				d.exports = function () {
					return function () {}
				}
			},
			function (d, p, i) {
				function e() {}
				function a(l) {
					var b = '' + l.type
					if (
						((p.BINARY_EVENT !== l.type && p.BINARY_ACK !== l.type) ||
							(b += l.attachments + '-'),
						l.nsp && l.nsp !== '/' && (b += l.nsp + ','),
						l.id != null && (b += l.id),
						l.data != null)
					) {
						var w = s(l.data)
						if (w === !1) return g
						b += w
					}
					return b
				}
				function s(l) {
					try {
						return JSON.stringify(l)
					} catch (b) {
						return !1
					}
				}
				function c(l, b) {
					function w(x) {
						var S = r.deconstructPacket(x),
							v = a(S.packet),
							k = S.buffers
						k.unshift(v), b(k)
					}
					r.removeBlobs(l, w)
				}
				function f() {
					this.reconstructor = null
				}
				function y(l) {
					var b = 0,
						w = { type: Number(l.charAt(0)) }
					if (p.types[w.type] == null) return n('unknown packet type ' + w.type)
					if (p.BINARY_EVENT === w.type || p.BINARY_ACK === w.type) {
						for (
							var x = '';
							l.charAt(++b) !== '-' && ((x += l.charAt(b)), b != l.length);

						);
						if (x != Number(x) || l.charAt(b) !== '-')
							throw new Error('Illegal attachments')
						w.attachments = Number(x)
					}
					if (l.charAt(b + 1) === '/')
						for (w.nsp = ''; ++b; ) {
							var S = l.charAt(b)
							if (S === ',' || ((w.nsp += S), b === l.length)) break
						}
					else w.nsp = '/'
					var v = l.charAt(b + 1)
					if (v !== '' && Number(v) == v) {
						for (w.id = ''; ++b; ) {
							var S = l.charAt(b)
							if (S == null || Number(S) != S) {
								--b
								break
							}
							if (((w.id += l.charAt(b)), b === l.length)) break
						}
						w.id = Number(w.id)
					}
					if (l.charAt(++b)) {
						var k = m(l.substr(b)),
							_ = k !== !1 && (w.type === p.ERROR || t(k))
						if (!_) return n('invalid payload')
						w.data = k
					}
					return w
				}
				function m(l) {
					try {
						return JSON.parse(l)
					} catch (b) {
						return !1
					}
				}
				function h(l) {
					;(this.reconPack = l), (this.buffers = [])
				}
				function n(l) {
					return { type: p.ERROR, data: 'parser error: ' + l }
				}
				var o = (i(3)('socket.io-parser'), i(5)),
					r = i(6),
					t = i(7),
					u = i(8)
				;(p.protocol = 4),
					(p.types = [
						'CONNECT',
						'DISCONNECT',
						'EVENT',
						'ACK',
						'ERROR',
						'BINARY_EVENT',
						'BINARY_ACK',
					]),
					(p.CONNECT = 0),
					(p.DISCONNECT = 1),
					(p.EVENT = 2),
					(p.ACK = 3),
					(p.ERROR = 4),
					(p.BINARY_EVENT = 5),
					(p.BINARY_ACK = 6),
					(p.Encoder = e),
					(p.Decoder = f)
				var g = p.ERROR + '"encode error"'
				;(e.prototype.encode = function (l, b) {
					if (p.BINARY_EVENT === l.type || p.BINARY_ACK === l.type) c(l, b)
					else {
						var w = a(l)
						b([w])
					}
				}),
					o(f.prototype),
					(f.prototype.add = function (l) {
						var b
						if (typeof l == 'string')
							(b = y(l)),
								p.BINARY_EVENT === b.type || p.BINARY_ACK === b.type
									? ((this.reconstructor = new h(b)),
									  this.reconstructor.reconPack.attachments === 0 &&
											this.emit('decoded', b))
									: this.emit('decoded', b)
						else {
							if (!u(l) && !l.base64) throw new Error('Unknown type: ' + l)
							if (!this.reconstructor)
								throw new Error(
									'got binary data when not reconstructing a packet'
								)
							;(b = this.reconstructor.takeBinaryData(l)),
								b && ((this.reconstructor = null), this.emit('decoded', b))
						}
					}),
					(f.prototype.destroy = function () {
						this.reconstructor && this.reconstructor.finishedReconstruction()
					}),
					(h.prototype.takeBinaryData = function (l) {
						if (
							(this.buffers.push(l),
							this.buffers.length === this.reconPack.attachments)
						) {
							var b = r.reconstructPacket(this.reconPack, this.buffers)
							return this.finishedReconstruction(), b
						}
						return null
					}),
					(h.prototype.finishedReconstruction = function () {
						;(this.reconPack = null), (this.buffers = [])
					})
			},
			function (d, p, i) {
				function e(s) {
					if (s) return a(s)
				}
				function a(s) {
					for (var c in e.prototype) s[c] = e.prototype[c]
					return s
				}
				;(d.exports = e),
					(e.prototype.on = e.prototype.addEventListener =
						function (s, c) {
							return (
								(this._callbacks = this._callbacks || {}),
								(this._callbacks['$' + s] =
									this._callbacks['$' + s] || []).push(c),
								this
							)
						}),
					(e.prototype.once = function (s, c) {
						function f() {
							this.off(s, f), c.apply(this, arguments)
						}
						return (f.fn = c), this.on(s, f), this
					}),
					(e.prototype.off =
						e.prototype.removeListener =
						e.prototype.removeAllListeners =
						e.prototype.removeEventListener =
							function (s, c) {
								if (
									((this._callbacks = this._callbacks || {}),
									arguments.length == 0)
								)
									return (this._callbacks = {}), this
								var f = this._callbacks['$' + s]
								if (!f) return this
								if (arguments.length == 1)
									return delete this._callbacks['$' + s], this
								for (var y, m = 0; m < f.length; m++)
									if (((y = f[m]), y === c || y.fn === c)) {
										f.splice(m, 1)
										break
									}
								return f.length === 0 && delete this._callbacks['$' + s], this
							}),
					(e.prototype.emit = function (s) {
						this._callbacks = this._callbacks || {}
						for (
							var c = new Array(arguments.length - 1),
								f = this._callbacks['$' + s],
								y = 1;
							y < arguments.length;
							y++
						)
							c[y - 1] = arguments[y]
						if (f) {
							f = f.slice(0)
							for (var y = 0, m = f.length; y < m; ++y) f[y].apply(this, c)
						}
						return this
					}),
					(e.prototype.listeners = function (s) {
						return (
							(this._callbacks = this._callbacks || {}),
							this._callbacks['$' + s] || []
						)
					}),
					(e.prototype.hasListeners = function (s) {
						return !!this.listeners(s).length
					})
			},
			function (d, p, i) {
				function e(h, n) {
					if (!h) return h
					if (c(h)) {
						var o = { _placeholder: !0, num: n.length }
						return n.push(h), o
					}
					if (s(h)) {
						for (var r = new Array(h.length), t = 0; t < h.length; t++)
							r[t] = e(h[t], n)
						return r
					}
					if (typeof h == 'object' && !(h instanceof Date)) {
						var r = {}
						for (var u in h) r[u] = e(h[u], n)
						return r
					}
					return h
				}
				function a(h, n) {
					if (!h) return h
					if (h && h._placeholder) return n[h.num]
					if (s(h)) for (var o = 0; o < h.length; o++) h[o] = a(h[o], n)
					else if (typeof h == 'object') for (var r in h) h[r] = a(h[r], n)
					return h
				}
				var s = i(7),
					c = i(8),
					f = Object.prototype.toString,
					y =
						typeof Blob == 'function' ||
						(typeof Blob != 'undefined' &&
							f.call(Blob) === '[object BlobConstructor]'),
					m =
						typeof File == 'function' ||
						(typeof File != 'undefined' &&
							f.call(File) === '[object FileConstructor]')
				;(p.deconstructPacket = function (h) {
					var n = [],
						o = h.data,
						r = h
					return (
						(r.data = e(o, n)),
						(r.attachments = n.length),
						{ packet: r, buffers: n }
					)
				}),
					(p.reconstructPacket = function (h, n) {
						return (h.data = a(h.data, n)), (h.attachments = void 0), h
					}),
					(p.removeBlobs = function (h, n) {
						function o(u, g, l) {
							if (!u) return u
							if ((y && u instanceof Blob) || (m && u instanceof File)) {
								r++
								var b = new FileReader()
								;(b.onload = function () {
									l ? (l[g] = this.result) : (t = this.result), --r || n(t)
								}),
									b.readAsArrayBuffer(u)
							} else if (s(u)) for (var w = 0; w < u.length; w++) o(u[w], w, u)
							else if (typeof u == 'object' && !c(u))
								for (var x in u) o(u[x], x, u)
						}
						var r = 0,
							t = h
						o(t), r || n(t)
					})
			},
			function (d, p) {
				var i = {}.toString
				d.exports =
					Array.isArray ||
					function (e) {
						return i.call(e) == '[object Array]'
					}
			},
			function (d, p) {
				function i(c) {
					return (
						(e && Buffer.isBuffer(c)) ||
						(a && (c instanceof ArrayBuffer || s(c)))
					)
				}
				d.exports = i
				var e =
						typeof Buffer == 'function' && typeof Buffer.isBuffer == 'function',
					a = typeof ArrayBuffer == 'function',
					s = function (c) {
						return typeof ArrayBuffer.isView == 'function'
							? ArrayBuffer.isView(c)
							: c.buffer instanceof ArrayBuffer
					}
			},
			function (d, p, i) {
				function e(t, u) {
					if (!(this instanceof e)) return new e(t, u)
					t &&
						(typeof t == 'undefined' ? 'undefined' : a(t)) === 'object' &&
						((u = t), (t = void 0)),
						(u = u || {}),
						(u.path = u.path || '/socket.io'),
						(this.nsps = {}),
						(this.subs = []),
						(this.opts = u),
						this.reconnection(u.reconnection !== !1),
						this.reconnectionAttempts(u.reconnectionAttempts || 1 / 0),
						this.reconnectionDelay(u.reconnectionDelay || 1e3),
						this.reconnectionDelayMax(u.reconnectionDelayMax || 5e3),
						this.randomizationFactor(u.randomizationFactor || 0.5),
						(this.backoff = new o({
							min: this.reconnectionDelay(),
							max: this.reconnectionDelayMax(),
							jitter: this.randomizationFactor(),
						})),
						this.timeout(u.timeout == null ? 2e4 : u.timeout),
						(this.readyState = 'closed'),
						(this.uri = t),
						(this.connecting = []),
						(this.lastPing = null),
						(this.encoding = !1),
						(this.packetBuffer = [])
					var g = u.parser || y
					;(this.encoder = new g.Encoder()),
						(this.decoder = new g.Decoder()),
						(this.autoConnect = u.autoConnect !== !1),
						this.autoConnect && this.open()
				}
				var a =
						typeof Symbol == 'function' && typeof Symbol.iterator == 'symbol'
							? function (t) {
									return typeof t
							  }
							: function (t) {
									return t &&
										typeof Symbol == 'function' &&
										t.constructor === Symbol &&
										t !== Symbol.prototype
										? 'symbol'
										: typeof t
							  },
					s = i(10),
					c = i(34),
					f = i(5),
					y = i(4),
					m = i(36),
					h = i(37),
					n = (i(3)('socket.io-client:manager'), i(33)),
					o = i(38),
					r = Object.prototype.hasOwnProperty
				;(d.exports = e),
					(e.prototype.emitAll = function () {
						this.emit.apply(this, arguments)
						for (var t in this.nsps)
							r.call(this.nsps, t) &&
								this.nsps[t].emit.apply(this.nsps[t], arguments)
					}),
					(e.prototype.updateSocketIds = function () {
						for (var t in this.nsps)
							r.call(this.nsps, t) && (this.nsps[t].id = this.generateId(t))
					}),
					(e.prototype.generateId = function (t) {
						return (t === '/' ? '' : t + '#') + this.engine.id
					}),
					f(e.prototype),
					(e.prototype.reconnection = function (t) {
						return arguments.length
							? ((this._reconnection = !!t), this)
							: this._reconnection
					}),
					(e.prototype.reconnectionAttempts = function (t) {
						return arguments.length
							? ((this._reconnectionAttempts = t), this)
							: this._reconnectionAttempts
					}),
					(e.prototype.reconnectionDelay = function (t) {
						return arguments.length
							? ((this._reconnectionDelay = t),
							  this.backoff && this.backoff.setMin(t),
							  this)
							: this._reconnectionDelay
					}),
					(e.prototype.randomizationFactor = function (t) {
						return arguments.length
							? ((this._randomizationFactor = t),
							  this.backoff && this.backoff.setJitter(t),
							  this)
							: this._randomizationFactor
					}),
					(e.prototype.reconnectionDelayMax = function (t) {
						return arguments.length
							? ((this._reconnectionDelayMax = t),
							  this.backoff && this.backoff.setMax(t),
							  this)
							: this._reconnectionDelayMax
					}),
					(e.prototype.timeout = function (t) {
						return arguments.length
							? ((this._timeout = t), this)
							: this._timeout
					}),
					(e.prototype.maybeReconnectOnOpen = function () {
						!this.reconnecting &&
							this._reconnection &&
							this.backoff.attempts === 0 &&
							this.reconnect()
					}),
					(e.prototype.open = e.prototype.connect =
						function (t, u) {
							if (~this.readyState.indexOf('open')) return this
							this.engine = s(this.uri, this.opts)
							var g = this.engine,
								l = this
							;(this.readyState = 'opening'), (this.skipReconnect = !1)
							var b = m(g, 'open', function () {
									l.onopen(), t && t()
								}),
								w = m(g, 'error', function (v) {
									if (
										(l.cleanup(),
										(l.readyState = 'closed'),
										l.emitAll('connect_error', v),
										t)
									) {
										var k = new Error('Connection error')
										;(k.data = v), t(k)
									} else l.maybeReconnectOnOpen()
								})
							if (this._timeout !== !1) {
								var x = this._timeout
								x === 0 && b.destroy()
								var S = setTimeout(function () {
									b.destroy(),
										g.close(),
										g.emit('error', 'timeout'),
										l.emitAll('connect_timeout', x)
								}, x)
								this.subs.push({
									destroy: function () {
										clearTimeout(S)
									},
								})
							}
							return this.subs.push(b), this.subs.push(w), this
						}),
					(e.prototype.onopen = function () {
						this.cleanup(), (this.readyState = 'open'), this.emit('open')
						var t = this.engine
						this.subs.push(m(t, 'data', h(this, 'ondata'))),
							this.subs.push(m(t, 'ping', h(this, 'onping'))),
							this.subs.push(m(t, 'pong', h(this, 'onpong'))),
							this.subs.push(m(t, 'error', h(this, 'onerror'))),
							this.subs.push(m(t, 'close', h(this, 'onclose'))),
							this.subs.push(m(this.decoder, 'decoded', h(this, 'ondecoded')))
					}),
					(e.prototype.onping = function () {
						;(this.lastPing = new Date()), this.emitAll('ping')
					}),
					(e.prototype.onpong = function () {
						this.emitAll('pong', new Date() - this.lastPing)
					}),
					(e.prototype.ondata = function (t) {
						this.decoder.add(t)
					}),
					(e.prototype.ondecoded = function (t) {
						this.emit('packet', t)
					}),
					(e.prototype.onerror = function (t) {
						this.emitAll('error', t)
					}),
					(e.prototype.socket = function (t, u) {
						function g() {
							~n(b.connecting, l) || b.connecting.push(l)
						}
						var l = this.nsps[t]
						if (!l) {
							;(l = new c(this, t, u)), (this.nsps[t] = l)
							var b = this
							l.on('connecting', g),
								l.on('connect', function () {
									l.id = b.generateId(t)
								}),
								this.autoConnect && g()
						}
						return l
					}),
					(e.prototype.destroy = function (t) {
						var u = n(this.connecting, t)
						~u && this.connecting.splice(u, 1),
							this.connecting.length || this.close()
					}),
					(e.prototype.packet = function (t) {
						var u = this
						t.query && t.type === 0 && (t.nsp += '?' + t.query),
							u.encoding
								? u.packetBuffer.push(t)
								: ((u.encoding = !0),
								  this.encoder.encode(t, function (g) {
										for (var l = 0; l < g.length; l++)
											u.engine.write(g[l], t.options)
										;(u.encoding = !1), u.processPacketQueue()
								  }))
					}),
					(e.prototype.processPacketQueue = function () {
						if (this.packetBuffer.length > 0 && !this.encoding) {
							var t = this.packetBuffer.shift()
							this.packet(t)
						}
					}),
					(e.prototype.cleanup = function () {
						for (var t = this.subs.length, u = 0; u < t; u++) {
							var g = this.subs.shift()
							g.destroy()
						}
						;(this.packetBuffer = []),
							(this.encoding = !1),
							(this.lastPing = null),
							this.decoder.destroy()
					}),
					(e.prototype.close = e.prototype.disconnect =
						function () {
							;(this.skipReconnect = !0),
								(this.reconnecting = !1),
								this.readyState === 'opening' && this.cleanup(),
								this.backoff.reset(),
								(this.readyState = 'closed'),
								this.engine && this.engine.close()
						}),
					(e.prototype.onclose = function (t) {
						this.cleanup(),
							this.backoff.reset(),
							(this.readyState = 'closed'),
							this.emit('close', t),
							this._reconnection && !this.skipReconnect && this.reconnect()
					}),
					(e.prototype.reconnect = function () {
						if (this.reconnecting || this.skipReconnect) return this
						var t = this
						if (this.backoff.attempts >= this._reconnectionAttempts)
							this.backoff.reset(),
								this.emitAll('reconnect_failed'),
								(this.reconnecting = !1)
						else {
							var u = this.backoff.duration()
							this.reconnecting = !0
							var g = setTimeout(function () {
								t.skipReconnect ||
									(t.emitAll('reconnect_attempt', t.backoff.attempts),
									t.emitAll('reconnecting', t.backoff.attempts),
									t.skipReconnect ||
										t.open(function (l) {
											l
												? ((t.reconnecting = !1),
												  t.reconnect(),
												  t.emitAll('reconnect_error', l.data))
												: t.onreconnect()
										}))
							}, u)
							this.subs.push({
								destroy: function () {
									clearTimeout(g)
								},
							})
						}
					}),
					(e.prototype.onreconnect = function () {
						var t = this.backoff.attempts
						;(this.reconnecting = !1),
							this.backoff.reset(),
							this.updateSocketIds(),
							this.emitAll('reconnect', t)
					})
			},
			function (d, p, i) {
				;(d.exports = i(11)), (d.exports.parser = i(19))
			},
			function (d, p, i) {
				function e(n, o) {
					return this instanceof e
						? ((o = o || {}),
						  n && typeof n == 'object' && ((o = n), (n = null)),
						  n
								? ((n = m(n)),
								  (o.hostname = n.host),
								  (o.secure = n.protocol === 'https' || n.protocol === 'wss'),
								  (o.port = n.port),
								  n.query && (o.query = n.query))
								: o.host && (o.hostname = m(o.host).host),
						  (this.secure =
								o.secure != null
									? o.secure
									: typeof location != 'undefined' &&
									  location.protocol === 'https:'),
						  o.hostname && !o.port && (o.port = this.secure ? '443' : '80'),
						  (this.agent = o.agent || !1),
						  (this.hostname =
								o.hostname ||
								(typeof location != 'undefined'
									? location.hostname
									: 'localhost')),
						  (this.port =
								o.port ||
								(typeof location != 'undefined' && location.port
									? location.port
									: this.secure
									? 443
									: 80)),
						  (this.query = o.query || {}),
						  typeof this.query == 'string' &&
								(this.query = h.decode(this.query)),
						  (this.upgrade = o.upgrade !== !1),
						  (this.path = (o.path || '/engine.io').replace(/\/$/, '') + '/'),
						  (this.forceJSONP = !!o.forceJSONP),
						  (this.jsonp = o.jsonp !== !1),
						  (this.forceBase64 = !!o.forceBase64),
						  (this.enablesXDR = !!o.enablesXDR),
						  (this.withCredentials = o.withCredentials !== !1),
						  (this.timestampParam = o.timestampParam || 't'),
						  (this.timestampRequests = o.timestampRequests),
						  (this.transports = o.transports || ['polling', 'websocket']),
						  (this.transportOptions = o.transportOptions || {}),
						  (this.readyState = ''),
						  (this.writeBuffer = []),
						  (this.prevBufferLen = 0),
						  (this.policyPort = o.policyPort || 843),
						  (this.rememberUpgrade = o.rememberUpgrade || !1),
						  (this.binaryType = null),
						  (this.onlyBinaryUpgrades = o.onlyBinaryUpgrades),
						  (this.perMessageDeflate =
								o.perMessageDeflate !== !1 && (o.perMessageDeflate || {})),
						  this.perMessageDeflate === !0 && (this.perMessageDeflate = {}),
						  this.perMessageDeflate &&
								this.perMessageDeflate.threshold == null &&
								(this.perMessageDeflate.threshold = 1024),
						  (this.pfx = o.pfx || null),
						  (this.key = o.key || null),
						  (this.passphrase = o.passphrase || null),
						  (this.cert = o.cert || null),
						  (this.ca = o.ca || null),
						  (this.ciphers = o.ciphers || null),
						  (this.rejectUnauthorized =
								o.rejectUnauthorized === void 0 || o.rejectUnauthorized),
						  (this.forceNode = !!o.forceNode),
						  (this.isReactNative =
								typeof navigator != 'undefined' &&
								typeof navigator.product == 'string' &&
								navigator.product.toLowerCase() === 'reactnative'),
						  (typeof self == 'undefined' || this.isReactNative) &&
								(o.extraHeaders &&
									Object.keys(o.extraHeaders).length > 0 &&
									(this.extraHeaders = o.extraHeaders),
								o.localAddress && (this.localAddress = o.localAddress)),
						  (this.id = null),
						  (this.upgrades = null),
						  (this.pingInterval = null),
						  (this.pingTimeout = null),
						  (this.pingIntervalTimer = null),
						  (this.pingTimeoutTimer = null),
						  void this.open())
						: new e(n, o)
				}
				function a(n) {
					var o = {}
					for (var r in n) n.hasOwnProperty(r) && (o[r] = n[r])
					return o
				}
				var s = i(12),
					c = i(5),
					f = (i(3)('engine.io-client:socket'), i(33)),
					y = i(19),
					m = i(2),
					h = i(27)
				;(d.exports = e),
					(e.priorWebsocketSuccess = !1),
					c(e.prototype),
					(e.protocol = y.protocol),
					(e.Socket = e),
					(e.Transport = i(18)),
					(e.transports = i(12)),
					(e.parser = i(19)),
					(e.prototype.createTransport = function (n) {
						var o = a(this.query)
						;(o.EIO = y.protocol), (o.transport = n)
						var r = this.transportOptions[n] || {}
						this.id && (o.sid = this.id)
						var t = new s[n]({
							query: o,
							socket: this,
							agent: r.agent || this.agent,
							hostname: r.hostname || this.hostname,
							port: r.port || this.port,
							secure: r.secure || this.secure,
							path: r.path || this.path,
							forceJSONP: r.forceJSONP || this.forceJSONP,
							jsonp: r.jsonp || this.jsonp,
							forceBase64: r.forceBase64 || this.forceBase64,
							enablesXDR: r.enablesXDR || this.enablesXDR,
							withCredentials: r.withCredentials || this.withCredentials,
							timestampRequests: r.timestampRequests || this.timestampRequests,
							timestampParam: r.timestampParam || this.timestampParam,
							policyPort: r.policyPort || this.policyPort,
							pfx: r.pfx || this.pfx,
							key: r.key || this.key,
							passphrase: r.passphrase || this.passphrase,
							cert: r.cert || this.cert,
							ca: r.ca || this.ca,
							ciphers: r.ciphers || this.ciphers,
							rejectUnauthorized:
								r.rejectUnauthorized || this.rejectUnauthorized,
							perMessageDeflate: r.perMessageDeflate || this.perMessageDeflate,
							extraHeaders: r.extraHeaders || this.extraHeaders,
							forceNode: r.forceNode || this.forceNode,
							localAddress: r.localAddress || this.localAddress,
							requestTimeout: r.requestTimeout || this.requestTimeout,
							protocols: r.protocols || void 0,
							isReactNative: this.isReactNative,
						})
						return t
					}),
					(e.prototype.open = function () {
						var n
						if (
							this.rememberUpgrade &&
							e.priorWebsocketSuccess &&
							this.transports.indexOf('websocket') !== -1
						)
							n = 'websocket'
						else {
							if (this.transports.length === 0) {
								var o = this
								return void setTimeout(function () {
									o.emit('error', 'No transports available')
								}, 0)
							}
							n = this.transports[0]
						}
						this.readyState = 'opening'
						try {
							n = this.createTransport(n)
						} catch (r) {
							return this.transports.shift(), void this.open()
						}
						n.open(), this.setTransport(n)
					}),
					(e.prototype.setTransport = function (n) {
						var o = this
						this.transport && this.transport.removeAllListeners(),
							(this.transport = n),
							n
								.on('drain', function () {
									o.onDrain()
								})
								.on('packet', function (r) {
									o.onPacket(r)
								})
								.on('error', function (r) {
									o.onError(r)
								})
								.on('close', function () {
									o.onClose('transport close')
								})
					}),
					(e.prototype.probe = function (n) {
						function o() {
							if (S.onlyBinaryUpgrades) {
								var v = !this.supportsBinary && S.transport.supportsBinary
								x = x || v
							}
							x ||
								(w.send([{ type: 'ping', data: 'probe' }]),
								w.once('packet', function (k) {
									if (!x)
										if (k.type === 'pong' && k.data === 'probe') {
											if (((S.upgrading = !0), S.emit('upgrading', w), !w))
												return
											;(e.priorWebsocketSuccess = w.name === 'websocket'),
												S.transport.pause(function () {
													x ||
														(S.readyState !== 'closed' &&
															(b(),
															S.setTransport(w),
															w.send([{ type: 'upgrade' }]),
															S.emit('upgrade', w),
															(w = null),
															(S.upgrading = !1),
															S.flush()))
												})
										} else {
											var _ = new Error('probe error')
											;(_.transport = w.name), S.emit('upgradeError', _)
										}
								}))
						}
						function r() {
							x || ((x = !0), b(), w.close(), (w = null))
						}
						function t(v) {
							var k = new Error('probe error: ' + v)
							;(k.transport = w.name), r(), S.emit('upgradeError', k)
						}
						function u() {
							t('transport closed')
						}
						function g() {
							t('socket closed')
						}
						function l(v) {
							w && v.name !== w.name && r()
						}
						function b() {
							w.removeListener('open', o),
								w.removeListener('error', t),
								w.removeListener('close', u),
								S.removeListener('close', g),
								S.removeListener('upgrading', l)
						}
						var w = this.createTransport(n, { probe: 1 }),
							x = !1,
							S = this
						;(e.priorWebsocketSuccess = !1),
							w.once('open', o),
							w.once('error', t),
							w.once('close', u),
							this.once('close', g),
							this.once('upgrading', l),
							w.open()
					}),
					(e.prototype.onOpen = function () {
						if (
							((this.readyState = 'open'),
							(e.priorWebsocketSuccess = this.transport.name === 'websocket'),
							this.emit('open'),
							this.flush(),
							this.readyState === 'open' &&
								this.upgrade &&
								this.transport.pause)
						)
							for (var n = 0, o = this.upgrades.length; n < o; n++)
								this.probe(this.upgrades[n])
					}),
					(e.prototype.onPacket = function (n) {
						if (
							this.readyState === 'opening' ||
							this.readyState === 'open' ||
							this.readyState === 'closing'
						)
							switch (
								(this.emit('packet', n), this.emit('heartbeat'), n.type)
							) {
								case 'open':
									this.onHandshake(JSON.parse(n.data))
									break
								case 'pong':
									this.setPing(), this.emit('pong')
									break
								case 'error':
									var o = new Error('server error')
									;(o.code = n.data), this.onError(o)
									break
								case 'message':
									this.emit('data', n.data), this.emit('message', n.data)
							}
					}),
					(e.prototype.onHandshake = function (n) {
						this.emit('handshake', n),
							(this.id = n.sid),
							(this.transport.query.sid = n.sid),
							(this.upgrades = this.filterUpgrades(n.upgrades)),
							(this.pingInterval = n.pingInterval),
							(this.pingTimeout = n.pingTimeout),
							this.onOpen(),
							this.readyState !== 'closed' &&
								(this.setPing(),
								this.removeListener('heartbeat', this.onHeartbeat),
								this.on('heartbeat', this.onHeartbeat))
					}),
					(e.prototype.onHeartbeat = function (n) {
						clearTimeout(this.pingTimeoutTimer)
						var o = this
						o.pingTimeoutTimer = setTimeout(function () {
							o.readyState !== 'closed' && o.onClose('ping timeout')
						}, n || o.pingInterval + o.pingTimeout)
					}),
					(e.prototype.setPing = function () {
						var n = this
						clearTimeout(n.pingIntervalTimer),
							(n.pingIntervalTimer = setTimeout(function () {
								n.ping(), n.onHeartbeat(n.pingTimeout)
							}, n.pingInterval))
					}),
					(e.prototype.ping = function () {
						var n = this
						this.sendPacket('ping', function () {
							n.emit('ping')
						})
					}),
					(e.prototype.onDrain = function () {
						this.writeBuffer.splice(0, this.prevBufferLen),
							(this.prevBufferLen = 0),
							this.writeBuffer.length === 0 ? this.emit('drain') : this.flush()
					}),
					(e.prototype.flush = function () {
						this.readyState !== 'closed' &&
							this.transport.writable &&
							!this.upgrading &&
							this.writeBuffer.length &&
							(this.transport.send(this.writeBuffer),
							(this.prevBufferLen = this.writeBuffer.length),
							this.emit('flush'))
					}),
					(e.prototype.write = e.prototype.send =
						function (n, o, r) {
							return this.sendPacket('message', n, o, r), this
						}),
					(e.prototype.sendPacket = function (n, o, r, t) {
						if (
							(typeof o == 'function' && ((t = o), (o = void 0)),
							typeof r == 'function' && ((t = r), (r = null)),
							this.readyState !== 'closing' && this.readyState !== 'closed')
						) {
							;(r = r || {}), (r.compress = r.compress !== !1)
							var u = { type: n, data: o, options: r }
							this.emit('packetCreate', u),
								this.writeBuffer.push(u),
								t && this.once('flush', t),
								this.flush()
						}
					}),
					(e.prototype.close = function () {
						function n() {
							t.onClose('forced close'), t.transport.close()
						}
						function o() {
							t.removeListener('upgrade', o),
								t.removeListener('upgradeError', o),
								n()
						}
						function r() {
							t.once('upgrade', o), t.once('upgradeError', o)
						}
						if (this.readyState === 'opening' || this.readyState === 'open') {
							this.readyState = 'closing'
							var t = this
							this.writeBuffer.length
								? this.once('drain', function () {
										this.upgrading ? r() : n()
								  })
								: this.upgrading
								? r()
								: n()
						}
						return this
					}),
					(e.prototype.onError = function (n) {
						;(e.priorWebsocketSuccess = !1),
							this.emit('error', n),
							this.onClose('transport error', n)
					}),
					(e.prototype.onClose = function (n, o) {
						if (
							this.readyState === 'opening' ||
							this.readyState === 'open' ||
							this.readyState === 'closing'
						) {
							var r = this
							clearTimeout(this.pingIntervalTimer),
								clearTimeout(this.pingTimeoutTimer),
								this.transport.removeAllListeners('close'),
								this.transport.close(),
								this.transport.removeAllListeners(),
								(this.readyState = 'closed'),
								(this.id = null),
								this.emit('close', n, o),
								(r.writeBuffer = []),
								(r.prevBufferLen = 0)
						}
					}),
					(e.prototype.filterUpgrades = function (n) {
						for (var o = [], r = 0, t = n.length; r < t; r++)
							~f(this.transports, n[r]) && o.push(n[r])
						return o
					})
			},
			function (d, p, i) {
				function e(y) {
					var m,
						h = !1,
						n = !1,
						o = y.jsonp !== !1
					if (typeof location != 'undefined') {
						var r = location.protocol === 'https:',
							t = location.port
						t || (t = r ? 443 : 80),
							(h = y.hostname !== location.hostname || t !== y.port),
							(n = y.secure !== r)
					}
					if (
						((y.xdomain = h),
						(y.xscheme = n),
						(m = new a(y)),
						'open' in m && !y.forceJSONP)
					)
						return new s(y)
					if (!o) throw new Error('JSONP disabled')
					return new c(y)
				}
				var a = i(13),
					s = i(16),
					c = i(30),
					f = i(31)
				;(p.polling = e), (p.websocket = f)
			},
			function (d, p, i) {
				var e = i(14),
					a = i(15)
				d.exports = function (s) {
					var c = s.xdomain,
						f = s.xscheme,
						y = s.enablesXDR
					try {
						if (typeof XMLHttpRequest != 'undefined' && (!c || e))
							return new XMLHttpRequest()
					} catch (m) {}
					try {
						if (typeof XDomainRequest != 'undefined' && !f && y)
							return new XDomainRequest()
					} catch (m) {}
					if (!c)
						try {
							return new a[['Active'].concat('Object').join('X')](
								'Microsoft.XMLHTTP'
							)
						} catch (m) {}
				}
			},
			function (d, p) {
				try {
					d.exports =
						typeof XMLHttpRequest != 'undefined' &&
						'withCredentials' in new XMLHttpRequest()
				} catch (i) {
					d.exports = !1
				}
			},
			function (d, p) {
				d.exports = (function () {
					return typeof self != 'undefined'
						? self
						: typeof window != 'undefined'
						? window
						: Function('return this')()
				})()
			},
			function (d, p, i) {
				function e() {}
				function a(r) {
					if (
						(y.call(this, r),
						(this.requestTimeout = r.requestTimeout),
						(this.extraHeaders = r.extraHeaders),
						typeof location != 'undefined')
					) {
						var t = location.protocol === 'https:',
							u = location.port
						u || (u = t ? 443 : 80),
							(this.xd =
								(typeof location != 'undefined' &&
									r.hostname !== location.hostname) ||
								u !== r.port),
							(this.xs = r.secure !== t)
					}
				}
				function s(r) {
					;(this.method = r.method || 'GET'),
						(this.uri = r.uri),
						(this.xd = !!r.xd),
						(this.xs = !!r.xs),
						(this.async = r.async !== !1),
						(this.data = r.data !== void 0 ? r.data : null),
						(this.agent = r.agent),
						(this.isBinary = r.isBinary),
						(this.supportsBinary = r.supportsBinary),
						(this.enablesXDR = r.enablesXDR),
						(this.withCredentials = r.withCredentials),
						(this.requestTimeout = r.requestTimeout),
						(this.pfx = r.pfx),
						(this.key = r.key),
						(this.passphrase = r.passphrase),
						(this.cert = r.cert),
						(this.ca = r.ca),
						(this.ciphers = r.ciphers),
						(this.rejectUnauthorized = r.rejectUnauthorized),
						(this.extraHeaders = r.extraHeaders),
						this.create()
				}
				function c() {
					for (var r in s.requests)
						s.requests.hasOwnProperty(r) && s.requests[r].abort()
				}
				var f = i(13),
					y = i(17),
					m = i(5),
					h = i(28),
					n = (i(3)('engine.io-client:polling-xhr'), i(15))
				if (
					((d.exports = a),
					(d.exports.Request = s),
					h(a, y),
					(a.prototype.supportsBinary = !0),
					(a.prototype.request = function (r) {
						return (
							(r = r || {}),
							(r.uri = this.uri()),
							(r.xd = this.xd),
							(r.xs = this.xs),
							(r.agent = this.agent || !1),
							(r.supportsBinary = this.supportsBinary),
							(r.enablesXDR = this.enablesXDR),
							(r.withCredentials = this.withCredentials),
							(r.pfx = this.pfx),
							(r.key = this.key),
							(r.passphrase = this.passphrase),
							(r.cert = this.cert),
							(r.ca = this.ca),
							(r.ciphers = this.ciphers),
							(r.rejectUnauthorized = this.rejectUnauthorized),
							(r.requestTimeout = this.requestTimeout),
							(r.extraHeaders = this.extraHeaders),
							new s(r)
						)
					}),
					(a.prototype.doWrite = function (r, t) {
						var u = typeof r != 'string' && r !== void 0,
							g = this.request({ method: 'POST', data: r, isBinary: u }),
							l = this
						g.on('success', t),
							g.on('error', function (b) {
								l.onError('xhr post error', b)
							}),
							(this.sendXhr = g)
					}),
					(a.prototype.doPoll = function () {
						var r = this.request(),
							t = this
						r.on('data', function (u) {
							t.onData(u)
						}),
							r.on('error', function (u) {
								t.onError('xhr poll error', u)
							}),
							(this.pollXhr = r)
					}),
					m(s.prototype),
					(s.prototype.create = function () {
						var r = {
							agent: this.agent,
							xdomain: this.xd,
							xscheme: this.xs,
							enablesXDR: this.enablesXDR,
						}
						;(r.pfx = this.pfx),
							(r.key = this.key),
							(r.passphrase = this.passphrase),
							(r.cert = this.cert),
							(r.ca = this.ca),
							(r.ciphers = this.ciphers),
							(r.rejectUnauthorized = this.rejectUnauthorized)
						var t = (this.xhr = new f(r)),
							u = this
						try {
							t.open(this.method, this.uri, this.async)
							try {
								if (this.extraHeaders) {
									t.setDisableHeaderCheck && t.setDisableHeaderCheck(!0)
									for (var g in this.extraHeaders)
										this.extraHeaders.hasOwnProperty(g) &&
											t.setRequestHeader(g, this.extraHeaders[g])
								}
							} catch (l) {}
							if (this.method === 'POST')
								try {
									this.isBinary
										? t.setRequestHeader(
												'Content-type',
												'application/octet-stream'
										  )
										: t.setRequestHeader(
												'Content-type',
												'text/plain;charset=UTF-8'
										  )
								} catch (l) {}
							try {
								t.setRequestHeader('Accept', '*/*')
							} catch (l) {}
							'withCredentials' in t &&
								(t.withCredentials = this.withCredentials),
								this.requestTimeout && (t.timeout = this.requestTimeout),
								this.hasXDR()
									? ((t.onload = function () {
											u.onLoad()
									  }),
									  (t.onerror = function () {
											u.onError(t.responseText)
									  }))
									: (t.onreadystatechange = function () {
											if (t.readyState === 2)
												try {
													var l = t.getResponseHeader('Content-Type')
													;((u.supportsBinary &&
														l === 'application/octet-stream') ||
														l === 'application/octet-stream; charset=UTF-8') &&
														(t.responseType = 'arraybuffer')
												} catch (b) {}
											t.readyState === 4 &&
												(t.status === 200 || t.status === 1223
													? u.onLoad()
													: setTimeout(function () {
															u.onError(
																typeof t.status == 'number' ? t.status : 0
															)
													  }, 0))
									  }),
								t.send(this.data)
						} catch (l) {
							return void setTimeout(function () {
								u.onError(l)
							}, 0)
						}
						typeof document != 'undefined' &&
							((this.index = s.requestsCount++),
							(s.requests[this.index] = this))
					}),
					(s.prototype.onSuccess = function () {
						this.emit('success'), this.cleanup()
					}),
					(s.prototype.onData = function (r) {
						this.emit('data', r), this.onSuccess()
					}),
					(s.prototype.onError = function (r) {
						this.emit('error', r), this.cleanup(!0)
					}),
					(s.prototype.cleanup = function (r) {
						if (typeof this.xhr != 'undefined' && this.xhr !== null) {
							if (
								(this.hasXDR()
									? (this.xhr.onload = this.xhr.onerror = e)
									: (this.xhr.onreadystatechange = e),
								r)
							)
								try {
									this.xhr.abort()
								} catch (t) {}
							typeof document != 'undefined' && delete s.requests[this.index],
								(this.xhr = null)
						}
					}),
					(s.prototype.onLoad = function () {
						var r
						try {
							var t
							try {
								t = this.xhr.getResponseHeader('Content-Type')
							} catch (u) {}
							r =
								t === 'application/octet-stream' ||
								t === 'application/octet-stream; charset=UTF-8'
									? this.xhr.response || this.xhr.responseText
									: this.xhr.responseText
						} catch (u) {
							this.onError(u)
						}
						r != null && this.onData(r)
					}),
					(s.prototype.hasXDR = function () {
						return (
							typeof XDomainRequest != 'undefined' &&
							!this.xs &&
							this.enablesXDR
						)
					}),
					(s.prototype.abort = function () {
						this.cleanup()
					}),
					(s.requestsCount = 0),
					(s.requests = {}),
					typeof document != 'undefined')
				) {
					if (typeof attachEvent == 'function') attachEvent('onunload', c)
					else if (typeof addEventListener == 'function') {
						var o = 'onpagehide' in n ? 'pagehide' : 'unload'
						addEventListener(o, c, !1)
					}
				}
			},
			function (d, p, i) {
				function e(h) {
					var n = h && h.forceBase64
					;(m && !n) || (this.supportsBinary = !1), a.call(this, h)
				}
				var a = i(18),
					s = i(27),
					c = i(19),
					f = i(28),
					y = i(29)
				i(3)('engine.io-client:polling'), (d.exports = e)
				var m = (function () {
					var h = i(13),
						n = new h({ xdomain: !1 })
					return n.responseType != null
				})()
				f(e, a),
					(e.prototype.name = 'polling'),
					(e.prototype.doOpen = function () {
						this.poll()
					}),
					(e.prototype.pause = function (h) {
						function n() {
							;(o.readyState = 'paused'), h()
						}
						var o = this
						if (
							((this.readyState = 'pausing'), this.polling || !this.writable)
						) {
							var r = 0
							this.polling &&
								(r++,
								this.once('pollComplete', function () {
									--r || n()
								})),
								this.writable ||
									(r++,
									this.once('drain', function () {
										--r || n()
									}))
						} else n()
					}),
					(e.prototype.poll = function () {
						;(this.polling = !0), this.doPoll(), this.emit('poll')
					}),
					(e.prototype.onData = function (h) {
						var n = this,
							o = function (r, t, u) {
								return (
									n.readyState === 'opening' && r.type === 'open' && n.onOpen(),
									r.type === 'close' ? (n.onClose(), !1) : void n.onPacket(r)
								)
							}
						c.decodePayload(h, this.socket.binaryType, o),
							this.readyState !== 'closed' &&
								((this.polling = !1),
								this.emit('pollComplete'),
								this.readyState === 'open' && this.poll())
					}),
					(e.prototype.doClose = function () {
						function h() {
							n.write([{ type: 'close' }])
						}
						var n = this
						this.readyState === 'open' ? h() : this.once('open', h)
					}),
					(e.prototype.write = function (h) {
						var n = this
						this.writable = !1
						var o = function () {
							;(n.writable = !0), n.emit('drain')
						}
						c.encodePayload(h, this.supportsBinary, function (r) {
							n.doWrite(r, o)
						})
					}),
					(e.prototype.uri = function () {
						var h = this.query || {},
							n = this.secure ? 'https' : 'http',
							o = ''
						this.timestampRequests !== !1 && (h[this.timestampParam] = y()),
							this.supportsBinary || h.sid || (h.b64 = 1),
							(h = s.encode(h)),
							this.port &&
								((n === 'https' && Number(this.port) !== 443) ||
									(n === 'http' && Number(this.port) !== 80)) &&
								(o = ':' + this.port),
							h.length && (h = '?' + h)
						var r = this.hostname.indexOf(':') !== -1
						return (
							n +
							'://' +
							(r ? '[' + this.hostname + ']' : this.hostname) +
							o +
							this.path +
							h
						)
					})
			},
			function (d, p, i) {
				function e(c) {
					;(this.path = c.path),
						(this.hostname = c.hostname),
						(this.port = c.port),
						(this.secure = c.secure),
						(this.query = c.query),
						(this.timestampParam = c.timestampParam),
						(this.timestampRequests = c.timestampRequests),
						(this.readyState = ''),
						(this.agent = c.agent || !1),
						(this.socket = c.socket),
						(this.enablesXDR = c.enablesXDR),
						(this.withCredentials = c.withCredentials),
						(this.pfx = c.pfx),
						(this.key = c.key),
						(this.passphrase = c.passphrase),
						(this.cert = c.cert),
						(this.ca = c.ca),
						(this.ciphers = c.ciphers),
						(this.rejectUnauthorized = c.rejectUnauthorized),
						(this.forceNode = c.forceNode),
						(this.isReactNative = c.isReactNative),
						(this.extraHeaders = c.extraHeaders),
						(this.localAddress = c.localAddress)
				}
				var a = i(19),
					s = i(5)
				;(d.exports = e),
					s(e.prototype),
					(e.prototype.onError = function (c, f) {
						var y = new Error(c)
						return (
							(y.type = 'TransportError'),
							(y.description = f),
							this.emit('error', y),
							this
						)
					}),
					(e.prototype.open = function () {
						return (
							(this.readyState !== 'closed' && this.readyState !== '') ||
								((this.readyState = 'opening'), this.doOpen()),
							this
						)
					}),
					(e.prototype.close = function () {
						return (
							(this.readyState !== 'opening' && this.readyState !== 'open') ||
								(this.doClose(), this.onClose()),
							this
						)
					}),
					(e.prototype.send = function (c) {
						if (this.readyState !== 'open')
							throw new Error('Transport not open')
						this.write(c)
					}),
					(e.prototype.onOpen = function () {
						;(this.readyState = 'open'), (this.writable = !0), this.emit('open')
					}),
					(e.prototype.onData = function (c) {
						var f = a.decodePacket(c, this.socket.binaryType)
						this.onPacket(f)
					}),
					(e.prototype.onPacket = function (c) {
						this.emit('packet', c)
					}),
					(e.prototype.onClose = function () {
						;(this.readyState = 'closed'), this.emit('close')
					})
			},
			function (d, p, i) {
				function e(v, k) {
					var _ = 'b' + p.packets[v.type] + v.data.data
					return k(_)
				}
				function a(v, k, _) {
					if (!k) return p.encodeBase64Packet(v, _)
					var A = v.data,
						E = new Uint8Array(A),
						R = new Uint8Array(1 + A.byteLength)
					R[0] = b[v.type]
					for (var N = 0; N < E.length; N++) R[N + 1] = E[N]
					return _(R.buffer)
				}
				function s(v, k, _) {
					if (!k) return p.encodeBase64Packet(v, _)
					var A = new FileReader()
					return (
						(A.onload = function () {
							p.encodePacket({ type: v.type, data: A.result }, k, !0, _)
						}),
						A.readAsArrayBuffer(v.data)
					)
				}
				function c(v, k, _) {
					if (!k) return p.encodeBase64Packet(v, _)
					if (l) return s(v, k, _)
					var A = new Uint8Array(1)
					A[0] = b[v.type]
					var E = new S([A.buffer, v.data])
					return _(E)
				}
				function f(v) {
					try {
						v = t.decode(v, { strict: !1 })
					} catch (k) {
						return !1
					}
					return v
				}
				function y(v, k, _) {
					for (
						var A = new Array(v.length),
							E = r(v.length, _),
							R = function (P, T, O) {
								k(T, function (D, q) {
									;(A[P] = q), O(D, A)
								})
							},
							N = 0;
						N < v.length;
						N++
					)
						R(N, v[N], E)
				}
				var m,
					h = i(20),
					n = i(21),
					o = i(22),
					r = i(23),
					t = i(24)
				typeof ArrayBuffer != 'undefined' && (m = i(25))
				var u =
						typeof navigator != 'undefined' &&
						/Android/i.test(navigator.userAgent),
					g =
						typeof navigator != 'undefined' &&
						/PhantomJS/i.test(navigator.userAgent),
					l = u || g
				p.protocol = 3
				var b = (p.packets = {
						open: 0,
						close: 1,
						ping: 2,
						pong: 3,
						message: 4,
						upgrade: 5,
						noop: 6,
					}),
					w = h(b),
					x = { type: 'error', data: 'parser error' },
					S = i(26)
				;(p.encodePacket = function (v, k, _, A) {
					typeof k == 'function' && ((A = k), (k = !1)),
						typeof _ == 'function' && ((A = _), (_ = null))
					var E = v.data === void 0 ? void 0 : v.data.buffer || v.data
					if (typeof ArrayBuffer != 'undefined' && E instanceof ArrayBuffer)
						return a(v, k, A)
					if (typeof S != 'undefined' && E instanceof S) return c(v, k, A)
					if (E && E.base64) return e(v, A)
					var R = b[v.type]
					return (
						v.data !== void 0 &&
							(R += _
								? t.encode(String(v.data), { strict: !1 })
								: String(v.data)),
						A('' + R)
					)
				}),
					(p.encodeBase64Packet = function (v, k) {
						var _ = 'b' + p.packets[v.type]
						if (typeof S != 'undefined' && v.data instanceof S) {
							var A = new FileReader()
							return (
								(A.onload = function () {
									var T = A.result.split(',')[1]
									k(_ + T)
								}),
								A.readAsDataURL(v.data)
							)
						}
						var E
						try {
							E = String.fromCharCode.apply(null, new Uint8Array(v.data))
						} catch (T) {
							for (
								var R = new Uint8Array(v.data), N = new Array(R.length), P = 0;
								P < R.length;
								P++
							)
								N[P] = R[P]
							E = String.fromCharCode.apply(null, N)
						}
						return (_ += btoa(E)), k(_)
					}),
					(p.decodePacket = function (v, k, _) {
						if (v === void 0) return x
						if (typeof v == 'string') {
							if (v.charAt(0) === 'b')
								return p.decodeBase64Packet(v.substr(1), k)
							if (_ && ((v = f(v)), v === !1)) return x
							var E = v.charAt(0)
							return Number(E) == E && w[E]
								? v.length > 1
									? { type: w[E], data: v.substring(1) }
									: { type: w[E] }
								: x
						}
						var A = new Uint8Array(v),
							E = A[0],
							R = o(v, 1)
						return (
							S && k === 'blob' && (R = new S([R])), { type: w[E], data: R }
						)
					}),
					(p.decodeBase64Packet = function (v, k) {
						var _ = w[v.charAt(0)]
						if (!m) return { type: _, data: { base64: !0, data: v.substr(1) } }
						var A = m.decode(v.substr(1))
						return k === 'blob' && S && (A = new S([A])), { type: _, data: A }
					}),
					(p.encodePayload = function (v, k, _) {
						function A(N) {
							return N.length + ':' + N
						}
						function E(N, P) {
							p.encodePacket(N, !!R && k, !1, function (T) {
								P(null, A(T))
							})
						}
						typeof k == 'function' && ((_ = k), (k = null))
						var R = n(v)
						return k && R
							? S && !l
								? p.encodePayloadAsBlob(v, _)
								: p.encodePayloadAsArrayBuffer(v, _)
							: v.length
							? void y(v, E, function (N, P) {
									return _(P.join(''))
							  })
							: _('0:')
					}),
					(p.decodePayload = function (v, k, _) {
						if (typeof v != 'string') return p.decodePayloadAsBinary(v, k, _)
						typeof k == 'function' && ((_ = k), (k = null))
						var A
						if (v === '') return _(x, 0, 1)
						for (var E, R, N = '', P = 0, T = v.length; P < T; P++) {
							var O = v.charAt(P)
							if (O === ':') {
								if (
									N === '' ||
									N != (E = Number(N)) ||
									((R = v.substr(P + 1, E)), N != R.length)
								)
									return _(x, 0, 1)
								if (R.length) {
									if (
										((A = p.decodePacket(R, k, !1)),
										x.type === A.type && x.data === A.data)
									)
										return _(x, 0, 1)
									var D = _(A, P + E, T)
									if (D === !1) return
								}
								;(P += E), (N = '')
							} else N += O
						}
						return N !== '' ? _(x, 0, 1) : void 0
					}),
					(p.encodePayloadAsArrayBuffer = function (v, k) {
						function _(A, E) {
							p.encodePacket(A, !0, !0, function (R) {
								return E(null, R)
							})
						}
						return v.length
							? void y(v, _, function (A, E) {
									var R = E.reduce(function (T, O) {
											var D
											return (
												(D = typeof O == 'string' ? O.length : O.byteLength),
												T + D.toString().length + D + 2
											)
										}, 0),
										N = new Uint8Array(R),
										P = 0
									return (
										E.forEach(function (T) {
											var O = typeof T == 'string',
												D = T
											if (O) {
												for (
													var q = new Uint8Array(T.length), L = 0;
													L < T.length;
													L++
												)
													q[L] = T.charCodeAt(L)
												D = q.buffer
											}
											O ? (N[P++] = 0) : (N[P++] = 1)
											for (
												var X = D.byteLength.toString(), L = 0;
												L < X.length;
												L++
											)
												N[P++] = parseInt(X[L])
											N[P++] = 255
											for (var q = new Uint8Array(D), L = 0; L < q.length; L++)
												N[P++] = q[L]
										}),
										k(N.buffer)
									)
							  })
							: k(new ArrayBuffer(0))
					}),
					(p.encodePayloadAsBlob = function (v, k) {
						function _(A, E) {
							p.encodePacket(A, !0, !0, function (R) {
								var N = new Uint8Array(1)
								if (((N[0] = 1), typeof R == 'string')) {
									for (
										var P = new Uint8Array(R.length), T = 0;
										T < R.length;
										T++
									)
										P[T] = R.charCodeAt(T)
									;(R = P.buffer), (N[0] = 0)
								}
								for (
									var O = R instanceof ArrayBuffer ? R.byteLength : R.size,
										D = O.toString(),
										q = new Uint8Array(D.length + 1),
										T = 0;
									T < D.length;
									T++
								)
									q[T] = parseInt(D[T])
								if (((q[D.length] = 255), S)) {
									var L = new S([N.buffer, q.buffer, R])
									E(null, L)
								}
							})
						}
						y(v, _, function (A, E) {
							return k(new S(E))
						})
					}),
					(p.decodePayloadAsBinary = function (v, k, _) {
						typeof k == 'function' && ((_ = k), (k = null))
						for (var A = v, E = []; A.byteLength > 0; ) {
							for (
								var R = new Uint8Array(A), N = R[0] === 0, P = '', T = 1;
								R[T] !== 255;
								T++
							) {
								if (P.length > 310) return _(x, 0, 1)
								P += R[T]
							}
							;(A = o(A, 2 + P.length)), (P = parseInt(P))
							var O = o(A, 0, P)
							if (N)
								try {
									O = String.fromCharCode.apply(null, new Uint8Array(O))
								} catch (L) {
									var D = new Uint8Array(O)
									O = ''
									for (var T = 0; T < D.length; T++)
										O += String.fromCharCode(D[T])
								}
							E.push(O), (A = o(A, P))
						}
						var q = E.length
						E.forEach(function (L, X) {
							_(p.decodePacket(L, k, !0), X, q)
						})
					})
			},
			function (d, p) {
				d.exports =
					Object.keys ||
					function (i) {
						var e = [],
							a = Object.prototype.hasOwnProperty
						for (var s in i) a.call(i, s) && e.push(s)
						return e
					}
			},
			function (d, p, i) {
				function e(y) {
					if (!y || typeof y != 'object') return !1
					if (a(y)) {
						for (var m = 0, h = y.length; m < h; m++) if (e(y[m])) return !0
						return !1
					}
					if (
						(typeof Buffer == 'function' &&
							Buffer.isBuffer &&
							Buffer.isBuffer(y)) ||
						(typeof ArrayBuffer == 'function' && y instanceof ArrayBuffer) ||
						(c && y instanceof Blob) ||
						(f && y instanceof File)
					)
						return !0
					if (
						y.toJSON &&
						typeof y.toJSON == 'function' &&
						arguments.length === 1
					)
						return e(y.toJSON(), !0)
					for (var n in y)
						if (Object.prototype.hasOwnProperty.call(y, n) && e(y[n])) return !0
					return !1
				}
				var a = i(7),
					s = Object.prototype.toString,
					c =
						typeof Blob == 'function' ||
						(typeof Blob != 'undefined' &&
							s.call(Blob) === '[object BlobConstructor]'),
					f =
						typeof File == 'function' ||
						(typeof File != 'undefined' &&
							s.call(File) === '[object FileConstructor]')
				d.exports = e
			},
			function (d, p) {
				d.exports = function (i, e, a) {
					var s = i.byteLength
					if (((e = e || 0), (a = a || s), i.slice)) return i.slice(e, a)
					if (
						(e < 0 && (e += s),
						a < 0 && (a += s),
						a > s && (a = s),
						e >= s || e >= a || s === 0)
					)
						return new ArrayBuffer(0)
					for (
						var c = new Uint8Array(i), f = new Uint8Array(a - e), y = e, m = 0;
						y < a;
						y++, m++
					)
						f[m] = c[y]
					return f.buffer
				}
			},
			function (d, p) {
				function i(a, s, c) {
					function f(m, h) {
						if (f.count <= 0) throw new Error('after called too many times')
						--f.count,
							m ? ((y = !0), s(m), (s = c)) : f.count !== 0 || y || s(null, h)
					}
					var y = !1
					return (c = c || e), (f.count = a), a === 0 ? s() : f
				}
				function e() {}
				d.exports = i
			},
			function (d, p) {
				function i(u) {
					for (var g, l, b = [], w = 0, x = u.length; w < x; )
						(g = u.charCodeAt(w++)),
							g >= 55296 && g <= 56319 && w < x
								? ((l = u.charCodeAt(w++)),
								  (64512 & l) == 56320
										? b.push(((1023 & g) << 10) + (1023 & l) + 65536)
										: (b.push(g), w--))
								: b.push(g)
					return b
				}
				function e(u) {
					for (var g, l = u.length, b = -1, w = ''; ++b < l; )
						(g = u[b]),
							g > 65535 &&
								((g -= 65536),
								(w += t(((g >>> 10) & 1023) | 55296)),
								(g = 56320 | (1023 & g))),
							(w += t(g))
					return w
				}
				function a(u, g) {
					if (u >= 55296 && u <= 57343) {
						if (g)
							throw Error(
								'Lone surrogate U+' +
									u.toString(16).toUpperCase() +
									' is not a scalar value'
							)
						return !1
					}
					return !0
				}
				function s(u, g) {
					return t(((u >> g) & 63) | 128)
				}
				function c(u, g) {
					if ((4294967168 & u) == 0) return t(u)
					var l = ''
					return (
						(4294965248 & u) == 0
							? (l = t(((u >> 6) & 31) | 192))
							: (4294901760 & u) == 0
							? (a(u, g) || (u = 65533),
							  (l = t(((u >> 12) & 15) | 224)),
							  (l += s(u, 6)))
							: (4292870144 & u) == 0 &&
							  ((l = t(((u >> 18) & 7) | 240)),
							  (l += s(u, 12)),
							  (l += s(u, 6))),
						(l += t((63 & u) | 128))
					)
				}
				function f(u, g) {
					g = g || {}
					for (
						var l, b = g.strict !== !1, w = i(u), x = w.length, S = -1, v = '';
						++S < x;

					)
						(l = w[S]), (v += c(l, b))
					return v
				}
				function y() {
					if (r >= o) throw Error('Invalid byte index')
					var u = 255 & n[r]
					if ((r++, (192 & u) == 128)) return 63 & u
					throw Error('Invalid continuation byte')
				}
				function m(u) {
					var g, l, b, w, x
					if (r > o) throw Error('Invalid byte index')
					if (r == o) return !1
					if (((g = 255 & n[r]), r++, (128 & g) == 0)) return g
					if ((224 & g) == 192) {
						if (((l = y()), (x = ((31 & g) << 6) | l), x >= 128)) return x
						throw Error('Invalid continuation byte')
					}
					if ((240 & g) == 224) {
						if (
							((l = y()),
							(b = y()),
							(x = ((15 & g) << 12) | (l << 6) | b),
							x >= 2048)
						)
							return a(x, u) ? x : 65533
						throw Error('Invalid continuation byte')
					}
					if (
						(248 & g) == 240 &&
						((l = y()),
						(b = y()),
						(w = y()),
						(x = ((7 & g) << 18) | (l << 12) | (b << 6) | w),
						x >= 65536 && x <= 1114111)
					)
						return x
					throw Error('Invalid UTF-8 detected')
				}
				function h(u, g) {
					g = g || {}
					var l = g.strict !== !1
					;(n = i(u)), (o = n.length), (r = 0)
					for (var b, w = []; (b = m(l)) !== !1; ) w.push(b)
					return e(w)
				}
				/*! https://mths.be/utf8js v2.1.2 by @mathias */ var n,
					o,
					r,
					t = String.fromCharCode
				d.exports = { version: '2.1.2', encode: f, decode: h }
			},
			function (d, p) {
				;(function (i) {
					;(p.encode = function (e) {
						var a,
							s = new Uint8Array(e),
							c = s.length,
							f = ''
						for (a = 0; a < c; a += 3)
							(f += i[s[a] >> 2]),
								(f += i[((3 & s[a]) << 4) | (s[a + 1] >> 4)]),
								(f += i[((15 & s[a + 1]) << 2) | (s[a + 2] >> 6)]),
								(f += i[63 & s[a + 2]])
						return (
							c % 3 === 2
								? (f = f.substring(0, f.length - 1) + '=')
								: c % 3 === 1 && (f = f.substring(0, f.length - 2) + '=='),
							f
						)
					}),
						(p.decode = function (e) {
							var a,
								s,
								c,
								f,
								y,
								m = 0.75 * e.length,
								h = e.length,
								n = 0
							e[e.length - 1] === '=' && (m--, e[e.length - 2] === '=' && m--)
							var o = new ArrayBuffer(m),
								r = new Uint8Array(o)
							for (a = 0; a < h; a += 4)
								(s = i.indexOf(e[a])),
									(c = i.indexOf(e[a + 1])),
									(f = i.indexOf(e[a + 2])),
									(y = i.indexOf(e[a + 3])),
									(r[n++] = (s << 2) | (c >> 4)),
									(r[n++] = ((15 & c) << 4) | (f >> 2)),
									(r[n++] = ((3 & f) << 6) | (63 & y))
							return o
						})
				})('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/')
			},
			function (d, p) {
				function i(m) {
					return m.map(function (h) {
						if (h.buffer instanceof ArrayBuffer) {
							var n = h.buffer
							if (h.byteLength !== n.byteLength) {
								var o = new Uint8Array(h.byteLength)
								o.set(new Uint8Array(n, h.byteOffset, h.byteLength)),
									(n = o.buffer)
							}
							return n
						}
						return h
					})
				}
				function e(m, h) {
					h = h || {}
					var n = new s()
					return (
						i(m).forEach(function (o) {
							n.append(o)
						}),
						h.type ? n.getBlob(h.type) : n.getBlob()
					)
				}
				function a(m, h) {
					return new Blob(i(m), h || {})
				}
				var s =
						typeof s != 'undefined'
							? s
							: typeof WebKitBlobBuilder != 'undefined'
							? WebKitBlobBuilder
							: typeof MSBlobBuilder != 'undefined'
							? MSBlobBuilder
							: typeof MozBlobBuilder != 'undefined' && MozBlobBuilder,
					c = (function () {
						try {
							var m = new Blob(['hi'])
							return m.size === 2
						} catch (h) {
							return !1
						}
					})(),
					f =
						c &&
						(function () {
							try {
								var m = new Blob([new Uint8Array([1, 2])])
								return m.size === 2
							} catch (h) {
								return !1
							}
						})(),
					y = s && s.prototype.append && s.prototype.getBlob
				typeof Blob != 'undefined' &&
					((e.prototype = Blob.prototype), (a.prototype = Blob.prototype)),
					(d.exports = (function () {
						return c ? (f ? Blob : a) : y ? e : void 0
					})())
			},
			function (d, p) {
				;(p.encode = function (i) {
					var e = ''
					for (var a in i)
						i.hasOwnProperty(a) &&
							(e.length && (e += '&'),
							(e += encodeURIComponent(a) + '=' + encodeURIComponent(i[a])))
					return e
				}),
					(p.decode = function (i) {
						for (
							var e = {}, a = i.split('&'), s = 0, c = a.length;
							s < c;
							s++
						) {
							var f = a[s].split('=')
							e[decodeURIComponent(f[0])] = decodeURIComponent(f[1])
						}
						return e
					})
			},
			function (d, p) {
				d.exports = function (i, e) {
					var a = function () {}
					;(a.prototype = e.prototype),
						(i.prototype = new a()),
						(i.prototype.constructor = i)
				}
			},
			function (d, p) {
				function i(n) {
					var o = ''
					do (o = c[n % f] + o), (n = Math.floor(n / f))
					while (n > 0)
					return o
				}
				function e(n) {
					var o = 0
					for (h = 0; h < n.length; h++) o = o * f + y[n.charAt(h)]
					return o
				}
				function a() {
					var n = i(+new Date())
					return n !== s ? ((m = 0), (s = n)) : n + '.' + i(m++)
				}
				for (
					var s,
						c =
							'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'.split(
								''
							),
						f = 64,
						y = {},
						m = 0,
						h = 0;
					h < f;
					h++
				)
					y[c[h]] = h
				;(a.encode = i), (a.decode = e), (d.exports = a)
			},
			function (d, p, i) {
				function e() {}
				function a(n) {
					s.call(this, n),
						(this.query = this.query || {}),
						y || (y = f.___eio = f.___eio || []),
						(this.index = y.length)
					var o = this
					y.push(function (r) {
						o.onData(r)
					}),
						(this.query.j = this.index),
						typeof addEventListener == 'function' &&
							addEventListener(
								'beforeunload',
								function () {
									o.script && (o.script.onerror = e)
								},
								!1
							)
				}
				var s = i(17),
					c = i(28),
					f = i(15)
				d.exports = a
				var y,
					m = /\n/g,
					h = /\\n/g
				c(a, s),
					(a.prototype.supportsBinary = !1),
					(a.prototype.doClose = function () {
						this.script &&
							(this.script.parentNode.removeChild(this.script),
							(this.script = null)),
							this.form &&
								(this.form.parentNode.removeChild(this.form),
								(this.form = null),
								(this.iframe = null)),
							s.prototype.doClose.call(this)
					}),
					(a.prototype.doPoll = function () {
						var n = this,
							o = document.createElement('script')
						this.script &&
							(this.script.parentNode.removeChild(this.script),
							(this.script = null)),
							(o.async = !0),
							(o.src = this.uri()),
							(o.onerror = function (u) {
								n.onError('jsonp poll error', u)
							})
						var r = document.getElementsByTagName('script')[0]
						r
							? r.parentNode.insertBefore(o, r)
							: (document.head || document.body).appendChild(o),
							(this.script = o)
						var t =
							typeof navigator != 'undefined' &&
							/gecko/i.test(navigator.userAgent)
						t &&
							setTimeout(function () {
								var u = document.createElement('iframe')
								document.body.appendChild(u), document.body.removeChild(u)
							}, 100)
					}),
					(a.prototype.doWrite = function (n, o) {
						function r() {
							t(), o()
						}
						function t() {
							if (u.iframe)
								try {
									u.form.removeChild(u.iframe)
								} catch (S) {
									u.onError('jsonp polling iframe removal error', S)
								}
							try {
								var x = '<iframe src="javascript:0" name="' + u.iframeId + '">'
								g = document.createElement(x)
							} catch (S) {
								;(g = document.createElement('iframe')),
									(g.name = u.iframeId),
									(g.src = 'javascript:0')
							}
							;(g.id = u.iframeId), u.form.appendChild(g), (u.iframe = g)
						}
						var u = this
						if (!this.form) {
							var g,
								l = document.createElement('form'),
								b = document.createElement('textarea'),
								w = (this.iframeId = 'eio_iframe_' + this.index)
							;(l.className = 'socketio'),
								(l.style.position = 'absolute'),
								(l.style.top = '-1000px'),
								(l.style.left = '-1000px'),
								(l.target = w),
								(l.method = 'POST'),
								l.setAttribute('accept-charset', 'utf-8'),
								(b.name = 'd'),
								l.appendChild(b),
								document.body.appendChild(l),
								(this.form = l),
								(this.area = b)
						}
						;(this.form.action = this.uri()),
							t(),
							(n = n.replace(
								h,
								`\\
`
							)),
							(this.area.value = n.replace(m, '\\n'))
						try {
							this.form.submit()
						} catch (x) {}
						this.iframe.attachEvent
							? (this.iframe.onreadystatechange = function () {
									u.iframe.readyState === 'complete' && r()
							  })
							: (this.iframe.onload = r)
					})
			},
			function (d, p, i) {
				function e(o) {
					var r = o && o.forceBase64
					r && (this.supportsBinary = !1),
						(this.perMessageDeflate = o.perMessageDeflate),
						(this.usingBrowserWebSocket = a && !o.forceNode),
						(this.protocols = o.protocols),
						this.usingBrowserWebSocket || (n = s),
						c.call(this, o)
				}
				var a,
					s,
					c = i(18),
					f = i(19),
					y = i(27),
					m = i(28),
					h = i(29)
				if (
					(i(3)('engine.io-client:websocket'),
					typeof WebSocket != 'undefined'
						? (a = WebSocket)
						: typeof self != 'undefined' &&
						  (a = self.WebSocket || self.MozWebSocket),
					typeof window == 'undefined')
				)
					try {
						s = i(32)
					} catch (o) {}
				var n = a || s
				;(d.exports = e),
					m(e, c),
					(e.prototype.name = 'websocket'),
					(e.prototype.supportsBinary = !0),
					(e.prototype.doOpen = function () {
						if (this.check()) {
							var o = this.uri(),
								r = this.protocols,
								t = {}
							this.isReactNative ||
								((t.agent = this.agent),
								(t.perMessageDeflate = this.perMessageDeflate),
								(t.pfx = this.pfx),
								(t.key = this.key),
								(t.passphrase = this.passphrase),
								(t.cert = this.cert),
								(t.ca = this.ca),
								(t.ciphers = this.ciphers),
								(t.rejectUnauthorized = this.rejectUnauthorized)),
								this.extraHeaders && (t.headers = this.extraHeaders),
								this.localAddress && (t.localAddress = this.localAddress)
							try {
								this.ws =
									this.usingBrowserWebSocket && !this.isReactNative
										? r
											? new n(o, r)
											: new n(o)
										: new n(o, r, t)
							} catch (u) {
								return this.emit('error', u)
							}
							this.ws.binaryType === void 0 && (this.supportsBinary = !1),
								this.ws.supports && this.ws.supports.binary
									? ((this.supportsBinary = !0),
									  (this.ws.binaryType = 'nodebuffer'))
									: (this.ws.binaryType = 'arraybuffer'),
								this.addEventListeners()
						}
					}),
					(e.prototype.addEventListeners = function () {
						var o = this
						;(this.ws.onopen = function () {
							o.onOpen()
						}),
							(this.ws.onclose = function () {
								o.onClose()
							}),
							(this.ws.onmessage = function (r) {
								o.onData(r.data)
							}),
							(this.ws.onerror = function (r) {
								o.onError('websocket error', r)
							})
					}),
					(e.prototype.write = function (o) {
						function r() {
							t.emit('flush'),
								setTimeout(function () {
									;(t.writable = !0), t.emit('drain')
								}, 0)
						}
						var t = this
						this.writable = !1
						for (var u = o.length, g = 0, l = u; g < l; g++)
							(function (b) {
								f.encodePacket(b, t.supportsBinary, function (w) {
									if (!t.usingBrowserWebSocket) {
										var x = {}
										if (
											(b.options && (x.compress = b.options.compress),
											t.perMessageDeflate)
										) {
											var S =
												typeof w == 'string' ? Buffer.byteLength(w) : w.length
											S < t.perMessageDeflate.threshold && (x.compress = !1)
										}
									}
									try {
										t.usingBrowserWebSocket ? t.ws.send(w) : t.ws.send(w, x)
									} catch (v) {}
									--u || r()
								})
							})(o[g])
					}),
					(e.prototype.onClose = function () {
						c.prototype.onClose.call(this)
					}),
					(e.prototype.doClose = function () {
						typeof this.ws != 'undefined' && this.ws.close()
					}),
					(e.prototype.uri = function () {
						var o = this.query || {},
							r = this.secure ? 'wss' : 'ws',
							t = ''
						this.port &&
							((r === 'wss' && Number(this.port) !== 443) ||
								(r === 'ws' && Number(this.port) !== 80)) &&
							(t = ':' + this.port),
							this.timestampRequests && (o[this.timestampParam] = h()),
							this.supportsBinary || (o.b64 = 1),
							(o = y.encode(o)),
							o.length && (o = '?' + o)
						var u = this.hostname.indexOf(':') !== -1
						return (
							r +
							'://' +
							(u ? '[' + this.hostname + ']' : this.hostname) +
							t +
							this.path +
							o
						)
					}),
					(e.prototype.check = function () {
						return !(
							!n ||
							('__initialize' in n && this.name === e.prototype.name)
						)
					})
			},
			function (d, p) {},
			function (d, p) {
				var i = [].indexOf
				d.exports = function (e, a) {
					if (i) return e.indexOf(a)
					for (var s = 0; s < e.length; ++s) if (e[s] === a) return s
					return -1
				}
			},
			function (d, p, i) {
				function e(t, u, g) {
					;(this.io = t),
						(this.nsp = u),
						(this.json = this),
						(this.ids = 0),
						(this.acks = {}),
						(this.receiveBuffer = []),
						(this.sendBuffer = []),
						(this.connected = !1),
						(this.disconnected = !0),
						(this.flags = {}),
						g && g.query && (this.query = g.query),
						this.io.autoConnect && this.open()
				}
				var a =
						typeof Symbol == 'function' && typeof Symbol.iterator == 'symbol'
							? function (t) {
									return typeof t
							  }
							: function (t) {
									return t &&
										typeof Symbol == 'function' &&
										t.constructor === Symbol &&
										t !== Symbol.prototype
										? 'symbol'
										: typeof t
							  },
					s = i(4),
					c = i(5),
					f = i(35),
					y = i(36),
					m = i(37),
					h = (i(3)('socket.io-client:socket'), i(27)),
					n = i(21)
				d.exports = e
				var o = {
						connect: 1,
						connect_error: 1,
						connect_timeout: 1,
						connecting: 1,
						disconnect: 1,
						error: 1,
						reconnect: 1,
						reconnect_attempt: 1,
						reconnect_failed: 1,
						reconnect_error: 1,
						reconnecting: 1,
						ping: 1,
						pong: 1,
					},
					r = c.prototype.emit
				c(e.prototype),
					(e.prototype.subEvents = function () {
						if (!this.subs) {
							var t = this.io
							this.subs = [
								y(t, 'open', m(this, 'onopen')),
								y(t, 'packet', m(this, 'onpacket')),
								y(t, 'close', m(this, 'onclose')),
							]
						}
					}),
					(e.prototype.open = e.prototype.connect =
						function () {
							return this.connected
								? this
								: (this.subEvents(),
								  this.io.reconnecting || this.io.open(),
								  this.io.readyState === 'open' && this.onopen(),
								  this.emit('connecting'),
								  this)
						}),
					(e.prototype.send = function () {
						var t = f(arguments)
						return t.unshift('message'), this.emit.apply(this, t), this
					}),
					(e.prototype.emit = function (t) {
						if (o.hasOwnProperty(t)) return r.apply(this, arguments), this
						var u = f(arguments),
							g = {
								type: (this.flags.binary !== void 0 ? this.flags.binary : n(u))
									? s.BINARY_EVENT
									: s.EVENT,
								data: u,
							}
						return (
							(g.options = {}),
							(g.options.compress = !this.flags || this.flags.compress !== !1),
							typeof u[u.length - 1] == 'function' &&
								((this.acks[this.ids] = u.pop()), (g.id = this.ids++)),
							this.connected ? this.packet(g) : this.sendBuffer.push(g),
							(this.flags = {}),
							this
						)
					}),
					(e.prototype.packet = function (t) {
						;(t.nsp = this.nsp), this.io.packet(t)
					}),
					(e.prototype.onopen = function () {
						if (this.nsp !== '/')
							if (this.query) {
								var t =
									a(this.query) === 'object' ? h.encode(this.query) : this.query
								this.packet({ type: s.CONNECT, query: t })
							} else this.packet({ type: s.CONNECT })
					}),
					(e.prototype.onclose = function (t) {
						;(this.connected = !1),
							(this.disconnected = !0),
							delete this.id,
							this.emit('disconnect', t)
					}),
					(e.prototype.onpacket = function (t) {
						var u = t.nsp === this.nsp,
							g = t.type === s.ERROR && t.nsp === '/'
						if (u || g)
							switch (t.type) {
								case s.CONNECT:
									this.onconnect()
									break
								case s.EVENT:
									this.onevent(t)
									break
								case s.BINARY_EVENT:
									this.onevent(t)
									break
								case s.ACK:
									this.onack(t)
									break
								case s.BINARY_ACK:
									this.onack(t)
									break
								case s.DISCONNECT:
									this.ondisconnect()
									break
								case s.ERROR:
									this.emit('error', t.data)
							}
					}),
					(e.prototype.onevent = function (t) {
						var u = t.data || []
						t.id != null && u.push(this.ack(t.id)),
							this.connected ? r.apply(this, u) : this.receiveBuffer.push(u)
					}),
					(e.prototype.ack = function (t) {
						var u = this,
							g = !1
						return function () {
							if (!g) {
								g = !0
								var l = f(arguments)
								u.packet({ type: n(l) ? s.BINARY_ACK : s.ACK, id: t, data: l })
							}
						}
					}),
					(e.prototype.onack = function (t) {
						var u = this.acks[t.id]
						typeof u == 'function' &&
							(u.apply(this, t.data), delete this.acks[t.id])
					}),
					(e.prototype.onconnect = function () {
						;(this.connected = !0),
							(this.disconnected = !1),
							this.emit('connect'),
							this.emitBuffered()
					}),
					(e.prototype.emitBuffered = function () {
						var t
						for (t = 0; t < this.receiveBuffer.length; t++)
							r.apply(this, this.receiveBuffer[t])
						for (
							this.receiveBuffer = [], t = 0;
							t < this.sendBuffer.length;
							t++
						)
							this.packet(this.sendBuffer[t])
						this.sendBuffer = []
					}),
					(e.prototype.ondisconnect = function () {
						this.destroy(), this.onclose('io server disconnect')
					}),
					(e.prototype.destroy = function () {
						if (this.subs) {
							for (var t = 0; t < this.subs.length; t++) this.subs[t].destroy()
							this.subs = null
						}
						this.io.destroy(this)
					}),
					(e.prototype.close = e.prototype.disconnect =
						function () {
							return (
								this.connected && this.packet({ type: s.DISCONNECT }),
								this.destroy(),
								this.connected && this.onclose('io client disconnect'),
								this
							)
						}),
					(e.prototype.compress = function (t) {
						return (this.flags.compress = t), this
					}),
					(e.prototype.binary = function (t) {
						return (this.flags.binary = t), this
					})
			},
			function (d, p) {
				function i(e, a) {
					var s = []
					a = a || 0
					for (var c = a || 0; c < e.length; c++) s[c - a] = e[c]
					return s
				}
				d.exports = i
			},
			function (d, p) {
				function i(e, a, s) {
					return (
						e.on(a, s),
						{
							destroy: function () {
								e.removeListener(a, s)
							},
						}
					)
				}
				d.exports = i
			},
			function (d, p) {
				var i = [].slice
				d.exports = function (e, a) {
					if ((typeof a == 'string' && (a = e[a]), typeof a != 'function'))
						throw new Error('bind() requires a function')
					var s = i.call(arguments, 2)
					return function () {
						return a.apply(e, s.concat(i.call(arguments)))
					}
				}
			},
			function (d, p) {
				function i(e) {
					;(e = e || {}),
						(this.ms = e.min || 100),
						(this.max = e.max || 1e4),
						(this.factor = e.factor || 2),
						(this.jitter = e.jitter > 0 && e.jitter <= 1 ? e.jitter : 0),
						(this.attempts = 0)
				}
				;(d.exports = i),
					(i.prototype.duration = function () {
						var e = this.ms * Math.pow(this.factor, this.attempts++)
						if (this.jitter) {
							var a = Math.random(),
								s = Math.floor(a * this.jitter * e)
							e = (1 & Math.floor(10 * a)) == 0 ? e - s : e + s
						}
						return 0 | Math.min(e, this.max)
					}),
					(i.prototype.reset = function () {
						this.attempts = 0
					}),
					(i.prototype.setMin = function (e) {
						this.ms = e
					}),
					(i.prototype.setMax = function (e) {
						this.max = e
					}),
					(i.prototype.setJitter = function (e) {
						this.jitter = e
					})
			},
		])
	})
})(ae)
var He = ae.exports
let Ie = window.location.hostname,
	ce = window.location.port ? ':9000' : '',
	Me = ce ? 'http' : 'https',
	Ue = `${Me}://${Ie}${ce}`,
	Ve = He(Ue),
	Fe = { resources: !0, call: !0, socketio: !0 }
var $e = {
	install(C, B = {}) {
		if (
			((B = Object.assign({}, Fe, B)),
			B.resources && C.use(je, B.resources),
			B.call)
		) {
			let d = typeof B.call == 'function' ? B.call : ie
			C.config.globalProperties.$call = d
		}
		B.socketio && (C.config.globalProperties.$socket = Ve)
	},
}
const ze = 'modulepreload',
	te = {},
	Xe = '/',
	W = function (B, d) {
		return !d || d.length === 0
			? B()
			: Promise.all(
					d.map((p) => {
						if (((p = `${Xe}${p}`), p in te)) return
						te[p] = !0
						const i = p.endsWith('.css'),
							e = i ? '[rel="stylesheet"]' : ''
						if (document.querySelector(`link[href="${p}"]${e}`)) return
						const a = document.createElement('link')
						if (
							((a.rel = i ? 'stylesheet' : ze),
							i || ((a.as = 'script'), (a.crossOrigin = '')),
							(a.href = p),
							document.head.appendChild(a),
							i)
						)
							return new Promise((s, c) => {
								a.addEventListener('load', s), a.addEventListener('error', c)
							})
					})
			  ).then(() => B())
	},
	Je = [
		{
			path: '/',
			name: 'Dashboards',
			component: () =>
				W(
					() => import('./Dashboards.0c604b74.js'),
					['assets/Dashboards.0c604b74.js', 'assets/vendor.851992cf.js']
				),
		},
		{
			path: '/query-builder',
			name: 'Builder',
			component: () =>
				W(
					() => import('./Builder.880e86c5.js'),
					['assets/Builder.880e86c5.js', 'assets/vendor.851992cf.js']
				),
		},
		{
			path: '/reports',
			name: 'Reports',
			component: () =>
				W(
					() => import('./Reports.1df4c90c.js'),
					['assets/Reports.1df4c90c.js', 'assets/vendor.851992cf.js']
				),
		},
		{
			path: '/settings',
			name: 'Settings',
			component: () =>
				W(
					() => import('./Settings.16ae9dd3.js'),
					['assets/Settings.16ae9dd3.js', 'assets/vendor.851992cf.js']
				),
		},
	]
let We = ye({ history: me('/analytics'), routes: Je })
const Ke = {},
	Ye = {
		xmlns: 'http://www.w3.org/2000/svg',
		width: '97',
		height: '22',
		viewBox: '0 0 97 22',
		fill: 'none',
	},
	Ze = j(
		'path',
		{ d: 'M10.0776 4H0V6.65083H10.0776V4Z', fill: '#0089FF' },
		null,
		-1
	),
	Ge = j(
		'path',
		{
			d: 'M0 10.7619V19.0708H3.21664V13.4171H9.40933V10.7619H0Z',
			fill: '#0089FF',
		},
		null,
		-1
	),
	Qe = j(
		'path',
		{
			d: 'M17.9723 18H15.4411L20.0497 4.90909H22.9773L27.5923 18H25.0611L21.5646 7.59375H21.4624L17.9723 18ZM18.0554 12.8672H24.9588V14.772H18.0554V12.8672ZM31.5282 12.2472V18H29.2143V8.18182H31.426V9.85014H31.541C31.7669 9.30043 32.127 8.86364 32.6213 8.53977C33.1199 8.21591 33.7356 8.05398 34.4686 8.05398C35.1461 8.05398 35.7363 8.19886 36.2392 8.48864C36.7463 8.77841 37.1383 9.19815 37.4153 9.74787C37.6966 10.2976 37.835 10.9645 37.8308 11.7486V18H35.5169V12.1065C35.5169 11.4503 35.3464 10.9368 35.0055 10.5661C34.6689 10.1953 34.2022 10.0099 33.6056 10.0099C33.2008 10.0099 32.8407 10.0994 32.5254 10.2784C32.2143 10.4531 31.9693 10.7067 31.7903 11.0391C31.6156 11.3714 31.5282 11.7741 31.5282 12.2472ZM43.0083 18.1982C42.3862 18.1982 41.8258 18.0874 41.3272 17.8658C40.8329 17.6399 40.4409 17.3075 40.1511 16.8686C39.8656 16.4297 39.7228 15.8885 39.7228 15.245C39.7228 14.6911 39.8251 14.233 40.0297 13.8707C40.2342 13.5085 40.5133 13.2188 40.867 13.0014C41.2207 12.7841 41.6191 12.62 42.0623 12.5092C42.5098 12.3942 42.9721 12.3111 43.4494 12.2599C44.0247 12.2003 44.4913 12.147 44.8493 12.1001C45.2072 12.049 45.4672 11.9723 45.6291 11.87C45.7953 11.7635 45.8784 11.5994 45.8784 11.3778V11.3395C45.8784 10.858 45.7356 10.4851 45.4501 10.2209C45.1646 9.95668 44.7534 9.82457 44.2164 9.82457C43.6497 9.82457 43.2001 9.94815 42.8677 10.1953C42.5396 10.4425 42.318 10.7344 42.2029 11.071L40.0424 10.7642C40.2129 10.1676 40.4941 9.66903 40.8862 9.26847C41.2782 8.86364 41.7576 8.56108 42.3244 8.3608C42.8912 8.15625 43.5176 8.05398 44.2037 8.05398C44.6767 8.05398 45.1476 8.10938 45.6163 8.22017C46.0851 8.33097 46.5133 8.5142 46.9011 8.76989C47.2889 9.02131 47.6 9.36435 47.8343 9.79901C48.073 10.2337 48.1923 10.777 48.1923 11.429V18H45.9679V16.6513H45.8912C45.7505 16.924 45.5524 17.1797 45.2967 17.4183C45.0453 17.6527 44.7278 17.8423 44.3443 17.9872C43.965 18.1278 43.5197 18.1982 43.0083 18.1982ZM43.6092 16.4979C44.0737 16.4979 44.4764 16.4062 44.8173 16.223C45.1582 16.0355 45.4203 15.7884 45.6035 15.4815C45.791 15.1747 45.8848 14.8402 45.8848 14.478V13.321C45.8123 13.3807 45.6887 13.4361 45.514 13.4872C45.3436 13.5384 45.1518 13.5831 44.9387 13.6214C44.7257 13.6598 44.5147 13.6939 44.3059 13.7237C44.0971 13.7536 43.916 13.7791 43.7626 13.8004C43.4174 13.8473 43.1085 13.924 42.8358 14.0305C42.563 14.1371 42.3478 14.2862 42.1902 14.478C42.0325 14.6655 41.9537 14.9084 41.9537 15.2067C41.9537 15.6328 42.1092 15.9545 42.4203 16.1719C42.7314 16.3892 43.1277 16.4979 43.6092 16.4979ZM52.8329 4.90909V18H50.519V4.90909H52.8329ZM56.6506 21.6818C56.3352 21.6818 56.0433 21.6563 55.7749 21.6051C55.5107 21.5582 55.2997 21.5028 55.142 21.4389L55.679 19.6364C56.0156 19.7344 56.3161 19.7813 56.5803 19.777C56.8445 19.7727 57.0767 19.6896 57.277 19.5277C57.4815 19.37 57.6541 19.1058 57.7947 18.7351L57.9929 18.2045L54.4325 8.18182H56.8871L59.1499 15.5966H59.2521L61.5213 8.18182H63.9822L60.0511 19.1889C59.8679 19.7088 59.625 20.1541 59.3224 20.5249C59.0199 20.8999 58.6491 21.1854 58.2102 21.3814C57.7756 21.5817 57.2557 21.6818 56.6506 21.6818ZM70.4862 8.18182V9.97159H64.842V8.18182H70.4862ZM66.2354 5.82955H68.5494V15.0469C68.5494 15.358 68.5962 15.5966 68.69 15.7628C68.788 15.9247 68.9158 16.0355 69.0735 16.0952C69.2312 16.1548 69.4059 16.1847 69.5977 16.1847C69.7425 16.1847 69.8746 16.174 69.994 16.1527C70.1175 16.1314 70.2113 16.1122 70.2752 16.0952L70.6651 17.9041C70.5415 17.9467 70.3647 17.9936 70.1346 18.0447C69.9087 18.0959 69.6317 18.1257 69.3036 18.1342C68.7241 18.1513 68.2021 18.0639 67.7376 17.8722C67.2731 17.6761 66.9045 17.3736 66.6317 16.9645C66.3633 16.5554 66.2312 16.044 66.2354 15.4304V5.82955ZM72.4213 18V8.18182H74.7353V18H72.4213ZM73.5847 6.78835C73.2182 6.78835 72.9029 6.6669 72.6387 6.42401C72.3745 6.17685 72.2424 5.88068 72.2424 5.53551C72.2424 5.18608 72.3745 4.88991 72.6387 4.64702C72.9029 4.39986 73.2182 4.27628 73.5847 4.27628C73.9554 4.27628 74.2708 4.39986 74.5307 4.64702C74.7949 4.88991 74.927 5.18608 74.927 5.53551C74.927 5.88068 74.7949 6.17685 74.5307 6.42401C74.2708 6.6669 73.9554 6.78835 73.5847 6.78835ZM81.3974 18.1918C80.4173 18.1918 79.5756 17.9766 78.8725 17.5462C78.1737 17.1158 77.6346 16.5213 77.2553 15.7628C76.8803 15 76.6928 14.1222 76.6928 13.1293C76.6928 12.1321 76.8846 11.2521 77.2681 10.4893C77.6516 9.7223 78.1928 9.12571 78.8917 8.69957C79.5948 8.26918 80.4258 8.05398 81.3846 8.05398C82.1815 8.05398 82.8867 8.20099 83.5004 8.49503C84.1183 8.7848 84.6104 9.19602 84.9769 9.72869C85.3434 10.2571 85.5522 10.875 85.6033 11.5824H83.3917C83.3022 11.1094 83.0891 10.7152 82.7525 10.3999C82.4201 10.0803 81.9748 9.92045 81.4165 9.92045C80.9435 9.92045 80.5281 10.0483 80.1701 10.304C79.8121 10.5554 79.533 10.9176 79.3327 11.3906C79.1367 11.8636 79.0387 12.4304 79.0387 13.0909C79.0387 13.7599 79.1367 14.3352 79.3327 14.8168C79.5288 15.294 79.8036 15.6626 80.1573 15.9226C80.5153 16.1783 80.935 16.3061 81.4165 16.3061C81.7575 16.3061 82.0621 16.2422 82.3306 16.1143C82.6033 15.9822 82.8313 15.7926 83.0146 15.5455C83.1978 15.2983 83.3235 14.9979 83.3917 14.6442H85.6033C85.5479 15.3388 85.3434 15.9545 84.9897 16.4915C84.636 17.0241 84.1545 17.4418 83.5451 17.7443C82.9357 18.0426 82.2198 18.1918 81.3974 18.1918ZM95.2633 10.777L93.1539 11.0071C93.0943 10.794 92.9899 10.5938 92.8407 10.4062C92.6958 10.2188 92.4998 10.0675 92.2527 9.95241C92.0055 9.83736 91.7029 9.77983 91.345 9.77983C90.8635 9.77983 90.4586 9.88423 90.1305 10.093C89.8066 10.3018 89.6468 10.5724 89.6511 10.9048C89.6468 11.1903 89.7512 11.4226 89.9643 11.6016C90.1816 11.7805 90.5396 11.9276 91.0382 12.0426L92.7129 12.4006C93.6419 12.6009 94.3322 12.9183 94.7839 13.353C95.2399 13.7876 95.47 14.3565 95.4743 15.0597C95.47 15.6776 95.2889 16.223 94.9309 16.696C94.5772 17.1648 94.085 17.5312 93.4544 17.7955C92.8237 18.0597 92.0993 18.1918 91.2811 18.1918C90.0794 18.1918 89.112 17.9403 88.3791 17.4375C87.6461 16.9304 87.2093 16.2251 87.0687 15.3217L89.3251 15.1044C89.4274 15.5476 89.6447 15.8821 89.9771 16.108C90.3095 16.3338 90.742 16.4467 91.2747 16.4467C91.8244 16.4467 92.2654 16.3338 92.5978 16.108C92.9345 15.8821 93.1028 15.603 93.1028 15.2706C93.1028 14.9893 92.9941 14.7571 92.7768 14.5739C92.5637 14.3906 92.2314 14.25 91.7797 14.152L90.1049 13.8004C89.1632 13.6044 88.4664 13.2741 88.0147 12.8097C87.563 12.3409 87.3393 11.7486 87.3436 11.0327C87.3393 10.4276 87.5034 9.90341 87.8358 9.46023C88.1724 9.01278 88.639 8.66761 89.2356 8.42472C89.8365 8.17756 90.5289 8.05398 91.313 8.05398C92.4636 8.05398 93.3691 8.29901 94.0297 8.78906C94.6944 9.27912 95.1056 9.94176 95.2633 10.777Z',
			fill: 'black',
		},
		null,
		-1
	),
	et = [Ze, Ge, Qe]
function tt(C, B) {
	return H(), F('svg', Ye, et)
}
var rt = z(Ke, [['render', tt]])
const nt = { name: 'App', components: { FrappeAnalyticsLogo: rt } },
	ot = { class: 'flex h-screen flex-col' },
	it = { class: 'bg-white shadow-sm' },
	st = { class: 'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8' },
	at = { class: 'flex h-16 justify-between' },
	ct = { class: 'flex' },
	ut = { class: 'flex flex-shrink-0 items-center' },
	ht = { class: 'hidden sm:-my-px sm:ml-6 sm:flex sm:space-x-8' },
	pt = $('Dashboards'),
	ft = $('Reports'),
	lt = $('Builder'),
	dt = $('Settings')
function yt(C, B, d, p, i, e) {
	const a = U('FrappeAnalyticsLogo'),
		s = U('router-link'),
		c = U('router-view')
	return (
		H(),
		F('div', ot, [
			j('nav', it, [
				j('div', st, [
					j('div', at, [
						j('div', ct, [
							j('div', ut, [I(a)]),
							j('div', ht, [
								I(
									s,
									{
										to: '/',
										class:
											'inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700',
										'aria-current': 'page',
									},
									{ default: J(() => [pt]), _: 1 }
								),
								I(
									s,
									{
										to: 'reports',
										class:
											'inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700',
										'aria-current': 'page',
									},
									{ default: J(() => [ft]), _: 1 }
								),
								I(
									s,
									{
										to: 'query-builder',
										class:
											'inline-flex items-center border-b-2 border-indigo-500 px-1 pt-1 text-sm font-medium text-gray-900',
										'aria-current': 'page',
									},
									{ default: J(() => [lt]), _: 1 }
								),
								I(
									s,
									{
										to: 'settings',
										class:
											'inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700',
										'aria-current': 'page',
									},
									{ default: J(() => [dt]), _: 1 }
								),
							]),
						]),
					]),
				]),
			]),
			I(c, { class: 'flex flex-1 flex-col' }),
		])
	)
}
var mt = z(nt, [['render', yt]])
let K = ge(mt)
K.use(We)
K.use($e)
K.component('Button', De)
K.mount('#app')
export { z as _, be as a }
