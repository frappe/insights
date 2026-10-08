import { describe, expect, it } from 'vitest'
import {
	DataStoreStorage,
	formatBytes,
	giveBackItems,
	storageSegments,
	StoredColumn,
	StoredTable,
	tableSegments,
} from './data_store_storage'

const MB = 1024 * 1024
const GB = 1024 * MB

function column(name: string, bytes: number, fields: Partial<StoredColumn> = {}): StoredColumn {
	return { name, bytes, readers: [], skipped: false, skippable: true, ...fields }
}

const reader = { doctype: 'Insights Query v3', name: 'q1', title: 'Jobs', workbook: '1' }

function table(
	name: string,
	columns: StoredColumn[],
	fields: Partial<StoredTable> = {},
): StoredTable {
	return {
		name,
		data_source: 'Site DB',
		table: `tab${name}`,
		label: name,
		sync_mode: 'Full',
		bytes: columns.reduce((sum, c) => sum + c.bytes, 0),
		rows: 100,
		measured_on: '2026-10-08 10:00:00',
		last_read_on: '2026-10-01 10:00:00',
		unread: false,
		columns,
		...fields,
	}
}

function storage(tables: StoredTable[], fields: Partial<DataStoreStorage> = {}): DataStoreStorage {
	return {
		measured_on: '2026-10-08 10:00:00',
		measuring: false,
		file_bytes: 10 * GB,
		free_bytes: 0,
		unread_days: 30,
		usage_known: true,
		cleanup: { stopped: false, stopped_on: null, last_run: null },
		groups: { read: 0, unread_columns: 0, unread_tables: 0, leftover: 0, other: 0, free: 0 },
		tables,
		leftover_tables: [],
		...fields,
	}
}

function described(items: ReturnType<typeof giveBackItems>) {
	return items.map((item) =>
		item.kind === 'column' ? `${item.table.name}.${item.column.name}` : item.table.name,
	)
}

describe('formatBytes', () => {
	// @feature data-store.storage-breakdown
	it('prints a size in GB from a gigabyte and in MB below it', () => {
		expect([72.1 * GB, 512 * MB, 2.5 * MB, 0].map(formatBytes)).toEqual([
			'72.1 GB',
			'512 MB',
			'2.5 MB',
			'0 MB',
		])
	})
})

describe('storageSegments', () => {
	// @feature data-store.storage-breakdown
	it('splits the file into its groups in a fixed order and leaves out an empty one', () => {
		const groups = {
			read: 4,
			unread_columns: 0,
			unread_tables: 3,
			leftover: 2,
			other: 1,
			free: 5,
		}
		expect(storageSegments(storage([], { groups })).map((s) => [s.key, s.value])).toEqual([
			['read', 4],
			['unread_tables', 3],
			['leftover', 2],
			['other', 1],
			['free', 5],
		])
	})
})

describe('tableSegments', () => {
	// @feature data-store.storage-breakdown
	it('splits a read table into the columns queries read and the ones none reads', () => {
		const jobs = table('Job', [
			column('name', 1 * MB, { readers: [reader] }),
			column('data', 9 * MB),
		])
		expect(tableSegments(storage([jobs]), jobs).map((s) => [s.key, s.value])).toEqual([
			['read', 1 * MB],
			['unread_columns', 9 * MB],
		])
	})
})

describe('giveBackItems', () => {
	// @feature data-store.give-back
	it('offers a table no query read in the window whole, not column by column', () => {
		const stale = table('Old', [column('a', MB), column('b', MB)], {
			last_read_on: '2026-06-01 10:00:00',
			unread: true,
		})
		const never = table('Never', [column('a', MB)], { last_read_on: null, unread: true })
		expect(described(giveBackItems(storage([stale, never])))).toEqual(['Old', 'Never'])
	})

	// @feature data-store.give-back
	it('offers a column no query or chart names, and not one a reader names', () => {
		const jobs = table('Job', [column('name', MB, { readers: [reader] }), column('data', MB)])
		expect(described(giveBackItems(storage([jobs])))).toEqual(['Job.data'])
	})

	// @feature data-store.give-back
	it('leaves out a column the import needs and one already skipped', () => {
		const jobs = table('Job', [
			column('modified', MB, { skippable: false }),
			column('data', MB, { skipped: true }),
		])
		expect(giveBackItems(storage([jobs]))).toEqual([])
	})

	// @feature data-store.give-back
	it('ranks tables and columns together, largest first', () => {
		const jobs = table('Job', [column('small', MB), column('large', 30 * MB)])
		const old = table('Old', [column('a', 10 * MB)], { last_read_on: null, unread: true })
		expect(described(giveBackItems(storage([jobs, old])))).toEqual([
			'Job.large',
			'Old',
			'Job.small',
		])
	})
})
