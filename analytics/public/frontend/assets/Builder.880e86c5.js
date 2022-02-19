import { _ as g, a as F } from './index.a22cb43d.js'
import {
	r as f,
	o,
	c as l,
	a as s,
	v as P,
	x as j,
	p as _,
	q as y,
	F as v,
	y as x,
	t as u,
	d as b,
	T as $,
	n as S,
	z as w,
	A as C,
} from './vendor.851992cf.js'
const I = {
		components: { FeatherIcon: F },
		data() {
			return { search_term: '', focused: !1, suggestions: [] }
		},
		resources: {
			table_list() {
				return {
					method: 'analytics.api.get_table_list',
					params: { search_term: this.search_term },
					auto: !0,
					onSuccess() {
						this.suggestions = this.table_list
					},
					debounce: 300,
				}
			},
		},
		computed: {
			table_list() {
				return this.$resources.table_list.data || []
			},
		},
		methods: {
			select_table(e) {
				;(this.search_term = ''),
					this.reset_suggestions(),
					this.$emit('table_selected', e)
			},
			reset_suggestions() {
				this.suggestions = this.table_list
			},
		},
	},
	N = { class: '' },
	B = { class: 'relative z-10 w-full rounded-md shadow-sm' },
	M = {
		class:
			'pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3',
	},
	z = {
		key: 0,
		class:
			'absolute top-10 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none',
	},
	E = ['onClick'],
	R = { class: 'flex items-center' },
	A = { class: 'font-semibold' }
function D(e, t, c, m, r, n) {
	const i = f('FeatherIcon')
	return (
		o(),
		l('div', N, [
			s('div', B, [
				P(
					s(
						'input',
						{
							type: 'text',
							name: 'table-search',
							class:
								'block w-full rounded-md border-gray-300 text-sm focus:border-gray-300 focus:shadow focus:outline-0 focus:ring-0',
							placeholder: 'Select a table...',
							'onUpdate:modelValue':
								t[0] || (t[0] = (a) => (r.search_term = a)),
							onFocus: t[1] || (t[1] = (a) => (r.focused = !0)),
							onBlur:
								t[2] ||
								(t[2] = (a) => {
									;[r.focused, r.search_term] = [!1, '']
								}),
						},
						null,
						544
					),
					[[j, r.search_term]]
				),
				s('div', M, [
					_(i, {
						name: 'search',
						class: 'h-5 w-5 text-gray-400',
						'aria-hidden': 'true',
					}),
				]),
				_(
					$,
					{
						'enter-active-class': 'transition ease-out duration-100',
						'enter-from-class': 'transform opacity-0 scale-95',
						'enter-to-class': 'transform opacity-100 scale-100',
						'leave-active-class': 'transition ease-in duration-75',
						'leave-from-class': 'transform opacity-100 scale-100',
						'leave-to-class': 'transform opacity-0 scale-95',
					},
					{
						default: y(() => [
							r.focused && r.suggestions.length != 0
								? (o(),
								  l('div', z, [
										(o(!0),
										l(
											v,
											null,
											x(
												r.suggestions,
												(a) => (
													o(),
													l(
														'div',
														{
															key: a.label,
															class:
																'flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900',
															onClick: (d) => n.select_table(a),
														},
														[s('div', R, [s('div', A, u(a.label), 1)])],
														8,
														E
													)
												)
											),
											128
										)),
								  ]))
								: b('', !0),
						]),
						_: 1,
					}
				),
			]),
		])
	)
}
var O = g(I, [['render', D]])
const Q = {},
	U = {
		xmlns: 'http://www.w3.org/2000/svg',
		width: '3',
		height: '10',
		viewBox: '0 0 2 10',
		fill: 'none',
	},
	V = s(
		'path',
		{
			'fill-rule': 'evenodd',
			'clip-rule': 'evenodd',
			d: 'M1 8C1.55228 8 2 8.44772 2 9C2 9.55228 1.55228 10 1 10C0.447715 10 0 9.55228 0 9C0 8.44772 0.447715 8 1 8ZM2 5C2 4.44772 1.55228 4 1 4C0.447715 4 0 4.44772 0 5C0 5.55228 0.447715 6 1 6C1.55228 6 2 5.55228 2 5ZM2 1C2 0.447715 1.55228 0 1 0C0.447715 0 0 0.447715 0 1C0 1.55229 0.447715 2 1 2C1.55228 2 2 1.55229 2 1Z',
			fill: '#969696',
		},
		null,
		-1
	),
	Z = [V]
function K(e, t) {
	return o(), l('svg', U, Z)
}
var L = g(Q, [['render', K]])
const q = {
		name: 'TablePicker',
		components: { TablePickerSearch: O, MenuIcon: L },
		data() {
			return {
				selected_tables: [],
				menu_open_for: void 0,
				menu_items: [{ label: 'Remove', is_danger_action: !0 }],
			}
		},
		mounted() {
			document.addEventListener('click', (e) => {
				e.target.closest('.menu-item') || (this.menu_open_for = void 0)
			}),
				this.on_table_select({ label: 'ToDo' })
		},
		methods: {
			on_table_select(e) {
				this.selected_tables.find((c) => c.label === e.label) ||
					(this.selected_tables.push(e),
					this.$emit('update:table_list', this.selected_tables))
			},
			on_menu_item_select(e, t) {
				e.is_danger_action &&
					(this.selected_tables.splice(t, 1),
					this.$emit('update:table_list', this.selected_tables),
					(this.menu_open_for = void 0))
			},
		},
	},
	G = { class: 'flex flex-col rounded bg-white p-4 shadow' },
	H = {
		key: 0,
		class:
			'flex flex-1 items-center justify-center rounded border-2 border-dashed border-gray-200 text-sm font-light text-gray-400',
	},
	J = s('p', null, 'Add tables to build report upon...', -1),
	W = [J],
	X = { key: 1, class: 'flex flex-1 select-none flex-col' },
	Y = ['onClick'],
	ee = { class: 'text-base font-medium' },
	te = { class: 'flex items-center' },
	se = { class: 'relative cursor-pointer rounded px-2 py-1' },
	re = {
		key: 0,
		class:
			'absolute right-2 top-6 z-10 origin-top-right rounded bg-white shadow-md ring-1 ring-slate-200',
	},
	oe = ['onClick']
function le(e, t, c, m, r, n) {
	const i = f('TablePickerSearch'),
		a = f('MenuIcon')
	return (
		o(),
		l('div', G, [
			_(i, { class: 'mb-4', onTable_selected: n.on_table_select }, null, 8, [
				'onTable_selected',
			]),
			r.selected_tables.length == 0
				? (o(), l('div', H, W))
				: (o(),
				  l('div', X, [
						(o(!0),
						l(
							v,
							null,
							x(
								r.selected_tables,
								(d, p) => (
									o(),
									l(
										'div',
										{
											key: p,
											class:
												'menu-item flex h-10 cursor-default items-center justify-between rounded border-b border-slate-200 pl-2 text-sm text-gray-700 hover:bg-slate-50 hover:ring-1 hover:ring-slate-100',
											onClick: (h) => (r.menu_open_for = p),
										},
										[
											s('div', ee, u(d.label), 1),
											s('div', te, [
												s('div', se, [
													_(a),
													_(
														$,
														{
															'enter-active-class':
																'transition ease-out duration-100',
															'enter-from-class':
																'transform opacity-0 scale-95',
															'enter-to-class':
																'transform opacity-100 scale-100',
															'leave-active-class':
																'transition ease-in duration-100',
															'leave-from-class':
																'transform opacity-100 scale-100',
															'leave-to-class': 'transform opacity-0 scale-95',
														},
														{
															default: y(() => [
																r.menu_open_for == p
																	? (o(),
																	  l('div', re, [
																			(o(!0),
																			l(
																				v,
																				null,
																				x(
																					r.menu_items,
																					(h, k) => (
																						o(),
																						l(
																							'div',
																							{
																								key: k,
																								class: S([
																									'cursor-pointer px-3 py-1',
																									h.is_header
																										? 'cursor-default border-b border-slate-200 text-xs font-light text-slate-400'
																										: h.is_danger_action
																										? 'border-t border-slate-200 text-red-400 hover:bg-slate-50'
																										: h.is_aggregation
																										? 'hover:bg-slate-50'
																										: '',
																								]),
																								onClick: (T) =>
																									n.on_menu_item_select(h, p),
																							},
																							u(h.label),
																							11,
																							oe
																						)
																					)
																				),
																				128
																			)),
																	  ]))
																	: b('', !0),
															]),
															_: 2,
														},
														1024
													),
												]),
											]),
										],
										8,
										Y
									)
								)
							),
							128
						)),
				  ])),
		])
	)
}
var ne = g(q, [['render', le]])
const ie = {
		components: { FeatherIcon: F },
		props: ['tables'],
		data() {
			return { search_term: '', focused: !1, suggestions: [] }
		},
		resources: {
			column_list() {
				return {
					method: 'analytics.api.get_column_list',
					params: { tables: this.tables },
					auto: !0,
					onSuccess() {
						this.suggestions = this.column_list
					},
				}
			},
		},
		computed: {
			column_list() {
				return this.$resources.column_list.data || []
			},
		},
		methods: {
			select_column(e) {
				;(this.search_term = ''),
					this.reset_suggestions(),
					this.$emit('column_selected', e)
			},
			reset_suggestions() {
				this.suggestions = this.column_list
			},
		},
		watch: {
			search_term(e) {
				if (!e) {
					this.reset_suggestions()
					return
				}
				this.suggestions = this.column_list.filter(
					(t) =>
						t.label.toLowerCase().includes(e.toLowerCase()) ||
						t.table.toLowerCase().includes(e.toLowerCase())
				)
			},
		},
	},
	ae = { class: '' },
	ce = { class: 'relative z-10 w-full rounded-md shadow-sm' },
	de = {
		class:
			'pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3',
	},
	ue = {
		key: 0,
		class:
			'absolute top-10 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none',
	},
	_e = ['onClick'],
	he = { class: 'flex items-center' },
	fe = { class: 'font-semibold' },
	me = { class: 'flex font-light text-slate-400' }
function pe(e, t, c, m, r, n) {
	const i = f('FeatherIcon')
	return (
		o(),
		l('div', ae, [
			s('div', ce, [
				P(
					s(
						'input',
						{
							type: 'text',
							name: 'column-search',
							class:
								'block w-full rounded-md border-gray-300 text-sm focus:border-gray-300 focus:shadow focus:outline-0 focus:ring-0',
							placeholder: 'Add a column...',
							'onUpdate:modelValue':
								t[0] || (t[0] = (a) => (r.search_term = a)),
							onFocus: t[1] || (t[1] = (a) => (r.focused = !0)),
							onBlur:
								t[2] ||
								(t[2] = (a) => {
									;[r.focused, r.search_term] = [!1, '']
								}),
						},
						null,
						544
					),
					[[j, r.search_term]]
				),
				s('div', de, [
					_(i, {
						name: 'search',
						class: 'h-5 w-5 text-gray-400',
						'aria-hidden': 'true',
					}),
				]),
				_(
					$,
					{
						'enter-active-class': 'transition ease-out duration-100',
						'enter-from-class': 'transform opacity-0 scale-95',
						'enter-to-class': 'transform opacity-100 scale-100',
						'leave-active-class': 'transition ease-in duration-75',
						'leave-from-class': 'transform opacity-100 scale-100',
						'leave-to-class': 'transform opacity-0 scale-95',
					},
					{
						default: y(() => [
							r.focused && r.suggestions.length != 0
								? (o(),
								  l('div', ue, [
										(o(!0),
										l(
											v,
											null,
											x(
												r.suggestions,
												(a) => (
													o(),
													l(
														'div',
														{
															key: a.label,
															class:
																'flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900',
															onClick: (d) => n.select_column(a),
														},
														[
															s('div', he, [s('div', fe, u(a.label), 1)]),
															s(
																'div',
																me,
																u(a.table) + '\xA0\u2022\xA0' + u(a.type),
																1
															),
														],
														8,
														_e
													)
												)
											),
											128
										)),
								  ]))
								: b('', !0),
						]),
						_: 1,
					}
				),
			]),
		])
	)
}
var ge = g(ie, [['render', pe]])
const be = {
		name: 'ColumnPicker',
		props: ['tables'],
		components: { ColumnPickerSearch: ge, MenuIcon: L },
		data() {
			return {
				selected_columns: [],
				menu_open_for: void 0,
				menu_items: [
					{ label: 'Aggregations', is_header: !0 },
					{ label: 'Group By', is_aggregation: !0 },
					{ label: 'Count', is_aggregation: !0 },
					{ label: 'Distinct', is_aggregation: !0 },
					{ label: 'Remove', is_danger_action: !0 },
				],
			}
		},
		mounted() {
			document.addEventListener('click', (e) => {
				e.target.closest('.menu-item') || (this.menu_open_for = void 0)
			})
		},
		methods: {
			on_column_select(e) {
				this.selected_columns.find(
					(c) => c.label === e.label && c.table === e.table
				) || this.selected_columns.push(e)
			},
			on_menu_item_select(e, t) {
				e.is_header ||
					(e.is_aggregation
						? (this.selected_columns[t].aggregation = e.label)
						: e.is_danger_action && this.selected_columns.splice(t, 1),
					(this.menu_open_for = void 0))
			},
		},
	},
	ve = { class: 'flex flex-col rounded bg-white p-4 shadow' },
	xe = {
		key: 0,
		class:
			'flex flex-1 items-center justify-center rounded border-2 border-dashed border-gray-200 text-sm font-light text-gray-400',
	},
	ye = s('p', null, 'No columns selected', -1),
	$e = [ye],
	ke = { key: 1, class: 'flex flex-1 select-none flex-col' },
	we = ['onClick'],
	Ce = { class: 'flex items-center' },
	Fe = { key: 0, class: 'my-0 font-medium text-blue-700' },
	Pe = { class: 'text-base font-medium' },
	je = { class: 'flex items-center' },
	Se = { class: 'mr-1 font-light text-slate-400' },
	Le = { class: 'relative cursor-pointer rounded px-2 py-1' },
	Te = {
		key: 0,
		class:
			'absolute right-2 top-6 z-10 origin-top-right rounded bg-white shadow-md ring-1 ring-slate-200',
	},
	Ie = ['onClick']
function Ne(e, t, c, m, r, n) {
	const i = f('ColumnPickerSearch'),
		a = f('MenuIcon')
	return (
		o(),
		l('div', ve, [
			_(
				i,
				{
					class: 'mb-4',
					onColumn_selected: n.on_column_select,
					tables: c.tables,
				},
				null,
				8,
				['onColumn_selected', 'tables']
			),
			r.selected_columns.length == 0
				? (o(), l('div', xe, $e))
				: (o(),
				  l('div', ke, [
						(o(!0),
						l(
							v,
							null,
							x(
								r.selected_columns,
								(d, p) => (
									o(),
									l(
										'div',
										{
											key: p,
											class:
												'menu-item flex h-10 cursor-default items-center justify-between rounded border-b border-slate-200 pl-2 text-sm text-gray-700 hover:bg-slate-50 hover:ring-1 hover:ring-slate-100',
											onClick: (h) => (r.menu_open_for = p),
										},
										[
											s('div', Ce, [
												d.aggregation
													? (o(),
													  l(
															'span',
															Fe,
															u(d.aggregation) + '\xA0\u2022\xA0 ',
															1
													  ))
													: b('', !0),
												s('div', Pe, u(d.label), 1),
											]),
											s('div', je, [
												s(
													'div',
													Se,
													u(d.table) + '\xA0\u2022\xA0' + u(d.type),
													1
												),
												s('div', Le, [
													_(a),
													_(
														$,
														{
															'enter-active-class':
																'transition ease-out duration-100',
															'enter-from-class':
																'transform opacity-0 scale-95',
															'enter-to-class':
																'transform opacity-100 scale-100',
															'leave-active-class':
																'transition ease-in duration-100',
															'leave-from-class':
																'transform opacity-100 scale-100',
															'leave-to-class': 'transform opacity-0 scale-95',
														},
														{
															default: y(() => [
																r.menu_open_for == p
																	? (o(),
																	  l('div', Te, [
																			(o(!0),
																			l(
																				v,
																				null,
																				x(
																					r.menu_items,
																					(h, k) => (
																						o(),
																						l(
																							'div',
																							{
																								key: k,
																								class: S([
																									'cursor-pointer px-3 py-1',
																									h.is_header
																										? 'cursor-default border-b border-slate-200 text-xs font-light text-slate-400'
																										: h.is_danger_action
																										? 'border-t border-slate-200 text-red-400 hover:bg-slate-50'
																										: h.is_aggregation
																										? 'hover:bg-slate-50'
																										: '',
																								]),
																								onClick: (T) =>
																									n.on_menu_item_select(h, p),
																							},
																							u(h.label),
																							11,
																							Ie
																						)
																					)
																				),
																				128
																			)),
																	  ]))
																	: b('', !0),
															]),
															_: 2,
														},
														1024
													),
												]),
											]),
										],
										8,
										we
									)
								)
							),
							128
						)),
				  ])),
		])
	)
}
var Be = g(be, [['render', Ne]])
const Me = {
		components: { FeatherIcon: F },
		props: ['tables', 'should_focus'],
		data() {
			return { focused: !1, input_value: '', delimiter: ';' }
		},
		mounted() {
			document.addEventListener('click', (e) => {
				var t
				if (
					e.target.closest('.filter-search') ||
					e.target.classList.contains('suggestion')
				)
					return (t = this.$refs.filter_search) == null ? void 0 : t.focus()
				this.focused = !1
			})
		},
		resources: {
			column_list() {
				return {
					method: 'analytics.api.get_column_list',
					params: { tables: this.tables },
					auto: !0,
					onSuccess() {
						this.column_list.forEach((e) => (e.left = !0))
					},
				}
			},
			operator_list() {
				return {
					method: 'analytics.api.get_operator_list',
					onSuccess() {
						this.operator_list.forEach((e) => (e.operator = !0))
					},
				}
			},
		},
		computed: {
			column_list() {
				return this.$resources.column_list.data || []
			},
			operator_list() {
				return this.$resources.operator_list.data || []
			},
			placeholder() {
				const [e, t, c] = this.input_value.split(this.delimiter)
				if (this.left_selected) {
					if (this.left_selected && !this.operator_selected) return 'operator'
					if (this.left_selected && this.operator_selected && !c)
						return 'type a string value...'
				} else return 'Select a column...'
			},
			left_selected() {
				return (this.input_value.match(/;/g) || []).length > 0
			},
			operator_selected() {
				return (this.input_value.match(/;/g) || []).length > 1
			},
			filter_left() {
				return this.input_value.split(this.delimiter)[0]
			},
			filter_operator() {
				return (this.input_value.split(this.delimiter)[1] || '').toLowerCase()
			},
			filter_right() {
				return this.input_value.split(this.delimiter)[2]
			},
			suggestions() {
				const [e, t, c] = this.input_value.split(this.delimiter)
				return this.left_selected
					? this.operator_selected
						? []
						: t
						? this.operator_list.filter((m) =>
								m.value.toLowerCase().includes(t.toLowerCase())
						  )
						: this.operator_list
					: e
					? this.column_list.filter((m) =>
							m.label.toLowerCase().includes(e.toLowerCase())
					  )
					: this.column_list
			},
		},
		methods: {
			on_suggestion_select(e) {
				e.left
					? (this.$resources.operator_list.submit({ fieldtype: e.type }),
					  (this.input_value = `${e.label}${this.delimiter}`))
					: e.operator &&
					  (this.input_value = `${this.filter_left}${this.delimiter}${e.value}${this.delimiter}`)
			},
			on_backspace(e) {
				const t = e.target.value.slice(-1)
				t &&
					t == this.delimiter &&
					(e.stopPropagation(),
					e.preventDefault(),
					(this.input_value = e.target.value
						.split(';')
						.filter((c) => c)
						.slice(0, -1)
						.map((c) => `${c};`)
						.join('')))
			},
			on_enter() {
				var e
				this.filter_left &&
					this.filter_operator &&
					this.filter_right &&
					(this.$emit('filter_selected', {
						left: this.filter_left,
						operator: this.filter_operator,
						right: this.filter_right,
					}),
					(this.input_value = ''),
					(this.focused = !1),
					(e = this.$refs.filter_search) == null || e.blur())
			},
		},
	},
	ze = { class: 'filter-search relative z-10 w-full rounded-md shadow-sm' },
	Ee = ['placeholder'],
	Re = {
		key: 0,
		class:
			'absolute top-0 block w-full cursor-text border border-transparent py-2 px-3 text-sm leading-6',
	},
	Ae = { class: 'mr-1 font-medium' },
	De = { class: 'mr-1 font-light' },
	Oe = { class: 'font-semibold text-green-600' },
	Qe = s(
		'div',
		{
			class:
				'absolute inset-y-0 right-0 flex items-center pr-3 transition-all hover:scale-110',
		},
		null,
		-1
	),
	Ue = {
		key: 0,
		class:
			'absolute top-10 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none',
	},
	Ve = ['onClick'],
	Ze = { class: 'flex items-center' },
	Ke = { class: 'font-semibold' },
	qe = { key: 0, class: 'flex font-light text-slate-400' }
function Ge(e, t, c, m, r, n) {
	return (
		o(),
		l('div', ze, [
			P(
				s(
					'input',
					{
						type: 'text',
						ref: 'filter_search',
						class:
							'block w-full select-none rounded-md border-gray-300 text-sm text-transparent caret-black focus:border-gray-300 focus:shadow focus:outline-0 focus:ring-0',
						placeholder: r.focused ? n.placeholder : 'Add a filter...',
						'onUpdate:modelValue': t[0] || (t[0] = (i) => (r.input_value = i)),
						onFocus: t[1] || (t[1] = (i) => (r.focused = !0)),
						onKeydown: [
							t[2] ||
								(t[2] = w(
									(...i) => n.on_backspace && n.on_backspace(...i),
									['backspace']
								)),
							t[3] ||
								(t[3] = w(
									C((...i) => n.on_enter && n.on_enter(...i), ['meta']),
									['enter']
								)),
							t[4] ||
								(t[4] = w(
									C((...i) => n.on_enter && n.on_enter(...i), ['ctrl']),
									['enter']
								)),
						],
					},
					null,
					40,
					Ee
				),
				[[j, r.input_value]]
			),
			r.input_value
				? (o(),
				  l('div', Re, [
						s('span', Ae, u(n.filter_left), 1),
						s('span', De, u(n.filter_operator), 1),
						s('span', Oe, u(n.filter_right), 1),
				  ]))
				: b('', !0),
			Qe,
			_(
				$,
				{
					'enter-active-class': 'transition ease-out duration-100',
					'enter-from-class': 'transform opacity-0 scale-95',
					'enter-to-class': 'transform opacity-100 scale-100',
					'leave-active-class': 'transition ease-in duration-75',
					'leave-from-class': 'transform opacity-100 scale-100',
					'leave-to-class': 'transform opacity-0 scale-95',
				},
				{
					default: y(() => [
						r.focused && n.suggestions.length != 0
							? (o(),
							  l('div', Ue, [
									(o(!0),
									l(
										v,
										null,
										x(
											n.suggestions,
											(i) => (
												o(),
												l(
													'div',
													{
														key: i.label,
														class:
															'suggestion flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900',
														onClick: C(
															(a) => n.on_suggestion_select(i),
															['prevent']
														),
													},
													[
														s('div', Ze, [s('div', Ke, u(i.label), 1)]),
														i.table
															? (o(),
															  l(
																	'div',
																	qe,
																	u(i.table) + '\xA0\u2022\xA0' + u(i.type),
																	1
															  ))
															: b('', !0),
													],
													8,
													Ve
												)
											)
										),
										128
									)),
							  ]))
							: b('', !0),
					]),
					_: 1,
				}
			),
		])
	)
}
var He = g(Me, [['render', Ge]])
const Je = { name: 'FilterNode', props: ['filters', 'operator'] },
	We = { class: 'relative ml-2 flex select-none flex-col pl-4' },
	Xe = s(
		'div',
		{
			class:
				'absolute -left-2 top-[20px] h-[calc(100%-40px)] w-1/3 rounded-lg border border-slate-300 bg-white',
		},
		null,
		-1
	),
	Ye = {
		class:
			'absolute -left-4 top-1/2 flex h-4 w-4 -translate-y-2 items-center justify-center rounded-full bg-white text-xs ring-1',
	},
	et = {
		key: 0,
		class:
			'group relative inline-flex h-10 w-fit cursor-default items-center justify-start rounded border border-slate-200 bg-white px-3 text-sm text-gray-700 filter transition-all',
	},
	tt = { class: 'mr-1 font-medium' },
	st = { class: 'mr-1 font-light' },
	rt = { class: 'font-semibold text-green-700' },
	ot = { key: 1 }
function lt(e, t, c, m, r, n) {
	const i = f('FilterNode', !0)
	return (
		o(),
		l('div', We, [
			Xe,
			s('span', Ye, u(c.operator), 1),
			(o(!0),
			l(
				v,
				null,
				x(
					Object.entries(c.filters[c.operator]),
					([a, d]) => (
						o(),
						l('div', { key: a, class: 'bg-white' }, [
							d && d.left
								? (o(),
								  l('div', et, [
										s('span', tt, u(d.left), 1),
										s('span', st, u(d.operator), 1),
										s('span', rt, u(d.right), 1),
								  ]))
								: d && (d['|'] || d['&'])
								? (o(),
								  l('div', ot, [
										_(i, { filters: d, operator: Object.keys(d)[0] }, null, 8, [
											'filters',
											'operator',
										]),
								  ]))
								: b('', !0),
						])
					)
				),
				128
			)),
		])
	)
}
var nt = g(Je, [['render', lt]])
const it = {
		name: 'FilterPicker',
		props: ['tables'],
		components: { FilterPickerSearch: He, FilterNode: nt },
		data() {
			return { filters: {}, root_operator: '&' }
		},
		methods: {
			on_filter_select(e) {
				this.filters[this.root_operator] ||
					(this.filters[this.root_operator] = {}),
					(this.filters[this.root_operator][
						Object.keys(this.filters[this.root_operator]).length
					] = e)
			},
		},
	},
	at = { class: 'flex flex-col rounded bg-white p-4 shadow' },
	ct = {
		key: 0,
		class:
			'flex flex-1 items-center justify-center rounded border-2 border-dashed border-gray-200 text-sm font-light text-gray-400',
	},
	dt = s('p', null, 'No filters added', -1),
	ut = [dt],
	_t = { key: 1, class: 'mx-2 flex flex-1 select-none flex-col' }
function ht(e, t, c, m, r, n) {
	const i = f('FilterPickerSearch'),
		a = f('FilterNode')
	return (
		o(),
		l('div', at, [
			_(
				i,
				{
					class: 'mb-4',
					ref: 'filter_search',
					onFilter_selected: n.on_filter_select,
					tables: c.tables,
				},
				null,
				8,
				['onFilter_selected', 'tables']
			),
			Object.keys(r.filters).length == 0
				? (o(), l('div', ct, ut))
				: (o(),
				  l('div', _t, [
						_(
							a,
							{ filters: r.filters, operator: Object.keys(r.filters)[0] },
							null,
							8,
							['filters', 'operator']
						),
				  ])),
		])
	)
}
var ft = g(it, [['render', ht]])
const mt = {},
	pt = { class: 'flex flex-1 items-center justify-center bg-white p-4 shadow' },
	gt = s(
		'div',
		{
			class:
				'cursor-pointer rounded bg-slate-100 px-2 py-1 text-sm font-light shadow ring-1 ring-slate-200',
		},
		' Run Query ',
		-1
	),
	bt = [gt]
function vt(e, t) {
	return o(), l('div', pt, bt)
}
var xt = g(mt, [['render', vt]])
const yt = {
		name: 'Builder',
		components: {
			ColumnPicker: Be,
			TablePicker: ne,
			FilterPicker: ft,
			QueryResult: xt,
		},
		data() {
			return { tables: [] }
		},
		computed: {
			table_names() {
				return this.tables.map((e) => e.label)
			},
		},
	},
	$t = { class: 'flex flex-1 flex-col py-10' },
	kt = s(
		'header',
		null,
		[
			s('div', { class: 'mx-auto max-w-7xl px-4 sm:px-6 lg:px-8' }, [
				s(
					'h1',
					{ class: 'text-3xl font-bold leading-tight text-gray-900' },
					' Query Builder '
				),
			]),
		],
		-1
	),
	wt = { class: 'flex flex-1' },
	Ct = { class: 'mx-auto flex max-w-7xl flex-1 sm:px-6 lg:px-8' },
	Ft = { class: 'my-8 grid flex-1 grid-flow-row gap-4' },
	Pt = { class: 'grid gap-4 sm:grid-cols-1 lg:grid-cols-3' },
	jt = { class: 'flex' }
function St(e, t, c, m, r, n) {
	const i = f('TablePicker'),
		a = f('ColumnPicker'),
		d = f('FilterPicker'),
		p = f('QueryResult')
	return (
		o(),
		l('div', $t, [
			kt,
			s('main', wt, [
				s('div', Ct, [
					s('div', Ft, [
						s('div', Pt, [
							_(i, {
								'onUpdate:table_list': t[0] || (t[0] = (h) => (r.tables = h)),
							}),
							_(a, { tables: n.table_names }, null, 8, ['tables']),
							_(d, { tables: n.table_names }, null, 8, ['tables']),
						]),
						s('div', jt, [_(p)]),
					]),
				]),
			]),
		])
	)
}
var It = g(yt, [['render', St]])
export { It as default }
