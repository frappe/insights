frappe.provide('insights.setup')

// redirect to desk page 'insights' after setup wizard is complete
// 'insights' desk page redirects to '/insights'
frappe.setup.welcome_page = '/app/insights'

frappe.setup.on('before_load', function () {
	insights.setup.slides_settings.map(frappe.setup.add_slide)
})

insights.setup.slides_settings = [
	{
		name: 'Database',
		title: __('Database Setup'),
		fields: get_database_setup_fields(),
		onload(slide) {
			this.attach_test_connection_listener(slide)
			this.attach_setup_demo_listener(slide)
			setTimeout(() => {
				slide.slides_footer.find('.complete-btn').hide()
			}, 500)
		},
		attach_test_connection_listener(slide) {
			const $test_conn_btn = slide.$body.find('.test-conn-btn')
			$test_conn_btn.on('click', () => {
				const values = slide.form.get_values(true)
				if (
					values.db_type &&
					values.db_name &&
					values.db_username &&
					values.db_password
				) {
					frappe.call({
						method: 'insights.setup.setup_wizard.test_db_connection',
						args: { db: values },
						callback: (r) => {
							if (r.message) {
								const success_msg = __(
									'Successfully connected to databse'
								)
								this.show_success_message(success_msg, slide)
							} else {
								frappe.show_alert({
									message: __(
										'Could not connect. Please check the credentials.'
									),
									indicator: 'orange',
								})
							}
						},
					})
				} else {
					frappe.show_alert({
						message: __(
							'You need to enter credentials to test the connection.'
						),
						indicator: 'orange',
					})
				}
			})
		},
		attach_setup_demo_listener(slide) {
			const $setup_demo_btn = slide.$body.find('.setup-demo-btn')
			$setup_demo_btn.click(() => {
				const success_msg = __(
					'Demo data will be imported once you complete the setup'
				)
				this.show_success_message(success_msg, slide)
				slide.get_field('setup_demo_db').set_value(1)
				slide.get_field('db_title').df.reqd = 0
				slide.get_field('db_name').df.reqd = 0
				slide.get_field('db_username').df.reqd = 0
				slide.get_field('db_password').df.reqd = 0
			})
		},
		show_success_section(slide) {
			slide.$body.find('.form-section').not(':last').hide()
		},
		show_success_message(message, slide) {
			slide.slides_footer.find('.complete-btn').show()
			this.show_success_section(slide)
			slide.get_field('success_html').$wrapper.append(
				`<div class="d-flex" style="flex-direction: column; align-items: center;">
					<div style="
							width: 40px; height: 40px;
							border-radius: 100%;
							display: flex; align-items: center;
							background-color: var(--green-500);
					">
						<svg class="icon icon-lg" style="stroke: white; stroke-width: 2px;">
							<use class="" href="#icon-tick"></use>
						</svg>
					</div>
					<br>
					<div class="text-muted text-center" style="width: 70%">${message}</div>
				</div>`
			)
		},
	},
]

function get_database_setup_fields() {
	return [
		{
			fieldtype: 'Select',
			fieldname: 'db_type',
			label: __('Database Type'),
			options: ['MariaDB'],
			default: 'MariaDB',
		},
		{
			fieldname: 'db_title',
			label: __('Title'),
			fieldtype: 'Data',
			reqd: 1,
		},
		{
			fieldname: 'db_host',
			fieldtype: 'Data',
			label: 'Host',
		},
		{
			fieldname: 'db_port',
			fieldtype: 'Data',
			label: 'Port',
		},
		{
			fieldname: 'column_break',
			fieldtype: 'Column Break',
		},
		{
			fieldname: 'db_name',
			fieldtype: 'Data',
			label: 'Database Name',
			reqd: 1,
		},
		{
			fieldname: 'db_username',
			fieldtype: 'Data',
			label: 'Username',
			reqd: 1,
		},
		{
			fieldname: 'db_password',
			fieldtype: 'Password',
			label: 'Password',
			reqd: 1,
		},
		{
			default: '0',
			fieldname: 'db_use_ssl',
			fieldtype: 'Check',
			label: 'Use SSL',
		},
		{
			fieldtype: 'Section Break',
			fieldname: 'section_break',
		},
		{
			fieldtype: 'HTML',
			fieldname: 'test_conn_html',
			options: get_test_conn_html(),
		},
		{
			fieldtype: 'HTML',
			fieldname: 'or_separator_html',
			options: get_separator_html(),
		},
		{
			fieldtype: 'HTML',
			fieldname: 'setup_demo_html',
			options: get_setup_demo_html(),
		},
		{
			fieldtype: 'Check',
			fieldname: 'setup_demo_db',
			hidden: 1,
		},
		{
			fieldtype: 'Section Break',
			fieldname: 'success_section_break',
		},
		{
			fieldtype: 'HTML',
			fieldname: 'success_html',
		},
	]
}

function get_separator_html() {
	return `
		<style>
			.or {
				display:flex;
				justify-content:center;
				align-items: center;
				color: var(--gray-600);
			}

			.or:after,
			.or:before {
					content: "";
					display: block;
					background: var(--gray-400);
					width: 30%;
					height:1px;
					margin: 0 10px;
			}
		</style>
		<div class="mt-4 or mb-4">OR</div>
	`
}

function get_test_conn_html() {
	return `
		<style>
			.test-conn-wrapper {
				display: flex;
				justify-content: center;
			}
		</style>
		<div class="test-conn-wrapper">
			<button class="test-conn-btn btn btn-xs btn-default">
				Test Connection
			</button>
		</div>
	`
}

function get_setup_demo_html() {
	return `
		<style>
			.setup-demo-wrapper {
				display: flex;
				justify-content: center;
			}
		</style>
		<div class="setup-demo-wrapper">
			<button class="setup-demo-btn btn btn-xs btn-default">
				Setup Demo Data
			</button>
		</div>
	`
}
