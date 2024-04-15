import { column, expression, table } from './query_utils'
import useQuery from './useQuery'

const query = useQuery()
query.addSource({ table: table('tabInvoice') })

query.addFilter({
	column: column('status'),
	operator: '==',
	value: 'Paid',
})
query.addFilter({
	column: column('docstatus'),
	operator: '==',
	value: 1,
})
query.addFilter({
	column: column('type'),
	operator: '==',
	value: 'Subscription',
})
query.addFilter({
	column: column('due_date'),
	operator: '>=',
	value: '2023-04-01',
})
query.addFilter({
	column: column('total'),
	operator: '!=',
	value: column('free_credits'),
})

query.addJoin({
	table: table('tabTeam'),
	left_column: column('team'),
	right_column: column('name'),
})

query.addMutate({
	label: 'month',
	mutation: column('due_date', { date_format: '%Y-%m-01' }),
})
query.addMutate({
	label: 'territory',
	mutation: column('custom_territory'),
})
query.addMutate({
	label: 'is_partner',
	mutation: column('erpnext_partner'),
})
query.addMutate({
	label: 'total_usd',
	mutation: expression(`
		case()
		.when(q.currency == "USD", q.total - q.free_credits)
		.else_((q.total - q.free_credits) / 83)
		.end()
	`),
})

query.addSummarize({
	metrics: { total_sales: column('total_usd', { aggregate: 'sum' }) },
	by: [column('team'), column('month'), column('user'), column('territory'), column('is_partner')],
})

query.addOrderBy({
	direction: 'asc',
	column: column('month'),
})

query.addMutate({
	label: 'mrr',
	mutation: expression(`q.total_sales.sum().over(group_by="month")`),
})
query.addMutate({
	label: 'amount_change',
	mutation: expression(
		`q.total_sales - q.total_sales.lag().over(group_by="user", order_by="month")`
	),
})
query.addMutate({
	label: 'invoice_no',
	mutation: expression(`row_number().over(group_by="user", order_by="month")`),
})
query.addMutate({
	label: 'change_type',
	mutation: expression(`
		case()
		.when(q.invoice_no == 0, "Expansion")
		.when(q.amount_change > 0, "Upsell")
		.when(q.amount_change < 0, "Contraction")
		.else_("Upsell")
		.end()
	`),
})

query.addSummarize({
	metrics: {
		total_sales: expression(`(
				case()
				.when(q.change_type == "Expansion", q.total_sales)
				.else_(q.amount_change)
				.end()
			).sum()
		`),
	},
	by: [column('month'), column('change_type')],
})

query.addPivotWider({
	id_cols: column('month'),
	names_from: column('change_type'),
	values_from: column('total_sales'),
	values_agg: 'sum',
})
query.addLimit(20)

export default query
