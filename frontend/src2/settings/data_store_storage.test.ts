import { describe, expect, it } from 'vitest'
import {
	columnState,
	DataStoreStorage,
	formatBytes,
	readersLabel,
	storageSegments,
	StoredColumn,
	StoredTable,
	tableSegments,
	unusedBytes,
} from './data_store_storage'

const MB = 1024 * 1024
const GB = 1024 * MB

function column(name: string, bytes: number, fields: Partial<StoredColumn> = {}): StoredColumn {
	return { name, bytes, readers: [], skipped: false, skippable: true, in_use: false, ...fields }
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
		read_bytes: 0,
		unread_bytes: 0,
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
		groups: { read: 0, unread_columns: 0, unread_tables: 0, cleanup: 0, other: 0, free: 0 },
		tables,
		cleanup_tables: [],
		...fields,
	}
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
			cleanup: 2,
			other: 1,
			free: 5,
		}
		expect(storageSegments(storage([], { groups })).map((s) => [s.key, s.value])).toEqual([
			['read', 4],
			['unread_tables', 3],
			['cleanup', 2],
			['other', 1],
			['free', 5],
		])
	})
})

describe('tableSegments', () => {
	// @feature data-store.storage-breakdown
	it('splits a read table into the bytes queries read and the bytes none reads', () => {
		const jobs = table('Job', [column('name', 1 * MB), column('data', 9 * MB)], {
			read_bytes: 1 * MB,
			unread_bytes: 9 * MB,
		})
		expect(tableSegments(storage([jobs]), jobs).map((s) => [s.key, s.value])).toEqual([
			['read', 1 * MB],
			['unread_columns', 9 * MB],
		])
	})

	// @feature data-store.storage-breakdown
	it('shows a table no query read in the window as one unread segment', () => {
		const old = table('Old', [column('a', 4 * MB)], { unread: true, unread_bytes: 4 * MB })
		expect(tableSegments(storage([old]), old).map((s) => [s.key, s.value])).toEqual([
			['unread_tables', 4 * MB],
		])
	})
})

describe('unusedBytes', () => {
	// @feature data-store.give-back
	it('counts the unread columns and the unread tables as unused', () => {
		const groups = {
			read: 4,
			unread_columns: 3,
			unread_tables: 2,
			cleanup: 1,
			other: 1,
			free: 5,
		}
		expect(unusedBytes(storage([], { groups }))).toBe(5)
	})
})

describe('columnState', () => {
	// @feature data-store.give-back
	it('offers to skip a column no query or chart names, and not one in use', () => {
		const states = [
			column('data', MB),
			column('name', MB, { readers: [reader], in_use: true }),
		].map(columnState)
		expect(states).toEqual(['unread', 'read'])
	})

	// @feature data-store.give-back
	it('leaves out a column the import needs and one already skipped', () => {
		const states = [
			column('modified', MB, { skippable: false, in_use: true }),
			column('data', MB, { skipped: true }),
		].map(columnState)
		expect(states).toEqual(['needed', 'skipped'])
	})
})

describe('readersLabel', () => {
	// @feature data-store.storage-breakdown
	it('counts queries, and says readers once another kind reads the column', () => {
		const team = { doctype: 'Insights Team', name: 't1', title: 'Sales', workbook: null }
		expect([[], [reader], [reader, reader], [reader, team]].map(readersLabel)).toEqual([
			'',
			'1 query',
			'2 queries',
			'2 readers',
		])
	})
})
