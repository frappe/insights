
export type DataSourceListItem = {
	title: string
	name: string
	owner: string
	status: 'Active' | 'Inactive'
	database_type: 'MariaDB' | 'PostgreSQL' | 'SQLite' | 'DuckDB'
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
}

type BaseDataSource = {
	title: string
	database_type: 'MariaDB' | 'PostgreSQL' | 'SQLite' | 'DuckDB'
	status?: 'Active' | 'Inactive'
}

export type MariaDBDataSource = BaseDataSource & {
	database_type: 'MariaDB'
	host: string
	port: number
	database_name: string
	username: string
	password: string
	use_ssl: boolean
}

export type PostgreSQLDataSource = BaseDataSource & {
	database_type: 'PostgreSQL'
	host: string
	port: number
	database_name: string
	username: string
	password: string
	use_ssl: boolean
}

export type DataSource = MariaDBDataSource | PostgreSQLDataSource
