import { column, expression, table } from './pipeline_utils'
import useQueryPipeline from './useQueryPipeline'

const pipeline = useQueryPipeline()
pipeline.addSource({ table: table('tabInvoice') })

pipeline.addFilter({
	column: column('status'),
	operator: '==',
	value: 'Paid',
})
pipeline.addFilter({
	column: column('docstatus'),
	operator: '==',
	value: 1,
})
pipeline.addFilter({
	column: column('type'),
	operator: '==',
	value: 'Subscription',
})
pipeline.addFilter({
	column: column('due_date'),
	operator: '>=',
	value: '2023-04-01',
})
pipeline.addFilter({
	column: column('total'),
	operator: '!=',
	value: column('free_credits'),
})

// pipeline.addJoin(table('tabTeam'), column('team'), column('name'))
pipeline.addJoin({
	table: table('tabTeam'),
	left_column: column('team'),
	right_column: column('name'),
})

pipeline.addMutate({
	label: 'month',
	mutation: column('due_date', { date_format: '%Y-%m-01' }),
})
pipeline.addMutate({
	label: 'territory',
	mutation: column('custom_territory'),
})
pipeline.addMutate({
	label: 'is_partner',
	mutation: column('erpnext_partner'),
})
pipeline.addMutate({
	label: 'total_usd',
	mutation: expression(`
		case()
		.when(q.currency == "USD", q.total - q.free_credits)
		.else_((q.total - q.free_credits) / 83)
		.end()
	`),
})

pipeline.addSummarize({
	metrics: { total_sales: column('total_usd', { aggregate: 'sum' }) },
	by: [column('team'), column('month'), column('user'), column('territory'), column('is_partner')],
})

pipeline.addOrderBy({
	direction: 'asc',
	column: column('month'),
})

pipeline.addMutate({
	label: 'mrr',
	mutation: expression(`q.total_sales.sum().over(group_by="month")`),
})
pipeline.addMutate({
	label: 'amount_change',
	mutation: expression(
		`q.total_sales - q.total_sales.lag().over(group_by="user", order_by="month")`
	),
})
pipeline.addMutate({
	label: 'invoice_no',
	mutation: expression(`row_number().over(group_by="user", order_by="month")`),
})
pipeline.addMutate({
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

pipeline.addSummarize({
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

pipeline.addPivotWider({
	id_cols: column('month'),
	names_from: column('change_type'),
	values_from: column('total_sales'),
	values_agg: 'sum',
})
pipeline.addLimit(20)

export default pipeline
