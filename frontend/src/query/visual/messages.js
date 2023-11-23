export const WARN_UNABLE_TO_INFER_JOIN = (table1, table2) => ({
	variant: 'warning',
	title: 'Unable to find a relationship',
	message: `Please add a relationship between ${table1} and ${table2} manually`,
})
export const ERROR_CANNOT_ADD_SELF_AS_TABLE = () => ({
	variant: 'error',
	title: 'Cannot add self as table',
	message: `Please select a different table`,
})
export const ERROR_UNABLE_TO_RESET_MAIN_TABLE = () => ({
	variant: 'error',
	title: 'Unable to reset main table',
	message: 'Please remove all columns and joins before resetting the main table',
})
