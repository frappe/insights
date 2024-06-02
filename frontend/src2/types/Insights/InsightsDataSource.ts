
export interface InsightsDataSource{
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Title : Data	*/
	title: string
	/**	Status : Select	*/
	status?: "Inactive" | "Active"
	/**	Database Type : Select	*/
	database_type?: "MariaDB" | "PostgreSQL" | "SQLite"
	/**	Site Database : Check	*/
	is_site_db?: 0 | 1
	/**	Host : Data	*/
	host?: string
	/**	Port : Data	*/
	port?: string
	/**	Use SSL : Check	*/
	use_ssl?: 0 | 1
	/**	Allow Table Import : Check	*/
	allow_imports?: 0 | 1
	/**	Database Name : Data	*/
	database_name?: string
	/**	Username : Data	*/
	username?: string
	/**	Password : Password	*/
	password?: string
	/**	Connection String : Password	*/
	connection_string?: string
}