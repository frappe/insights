describe('QueryList', () => {
	it('checks if query list is rendered', () => {
		cy.intercept('insights.api.get_queries', {
			message: [
				{
					name: 'test_query',
					title: 'Test Query',
					tables: 'Test Table',
					data_source: 'Test Data Source',
					modified: '2020-01-01 00:00:00',
				},
			],
		}).as('getQueries')

		// check if query list is rendered with one query
		cy.visit('/insights/query')
		cy.wait('@getQueries')
		cy.get('ul[role="list"]').should('not.be.empty').as('queryList')
		cy.get('@queryList').find('li').as('query').should('have.length', 1)

		// check if clicking on query routes to query page
		cy.intercept('frappe.client.get', { message: {} }).as('getQuery')
		cy.get('@query').click()
		cy.wait('@getQuery')
		cy.url().should('include', '/insights/query/test_query')
	})
})
