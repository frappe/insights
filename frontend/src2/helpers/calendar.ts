// The calendar the site counts by, in the browser.
//
// A week does not start on the same day everywhere and a fiscal year does not
// start in January everywhere, and both are site settings: `week_starts_on` and
// `fiscal_year_start` on `Insights Settings`, sent with the site info so a guest
// on a public link gets them too. dayjs knows neither, so a span the browser
// resolves through `startOf('week')` landed on a different Monday from the one
// `get_first_day_of_week` lands on, and a fiscal year had no dayjs unit at all.
//
// The server's answer is `get_current_date_range` in `sql_functions.py`. This is
// the same answer in dayjs, for the range a picker prints before the query runs.

import type { Dayjs } from 'dayjs'
import dayjs from './dayjs'
import session from '../session'
import type { SpanUnit } from './span_grammar'

/** What the server falls back to, in `get_fiscal_year_start_date`. */
const FISCAL_YEAR_START = '1995-04-01'

/** Monday-first, the way `Insights Settings` lists the days. */
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

/** The week's first day as dayjs numbers it: Sunday 0 through Saturday 6. */
function weekStartDay(): number {
	const index = WEEKDAYS.indexOf(session.site?.week_starts_on || 'Monday')
	return ((index < 0 ? 0 : index) + 1) % 7
}

/** The month and day a fiscal year starts on. */
function fiscalYearStart(): { month: number; date: number } {
	const start = dayjs(session.site?.fiscal_year_start || FISCAL_YEAR_START)
	return start.isValid() ? { month: start.month(), date: start.date() } : { month: 3, date: 1 }
}

/** The first day of the period of `unit` that `date` falls in. */
export function startOfPeriod(date: Dayjs, unit: SpanUnit): Dayjs {
	if (unit === 'week') {
		return date.subtract((date.day() - weekStartDay() + 7) % 7, 'day').startOf('day')
	}
	if (unit === 'fiscal year') {
		const { month, date: day } = fiscalYearStart()
		const start = date.month(month).date(day).startOf('day')
		return date.isBefore(start) ? start.subtract(1, 'year') : start
	}
	// dayjs types `quarter` only through the plugin `helpers/dayjs` loads
	return date.startOf(unit as any)
}

/** The last day of the period of `unit` that `date` falls in. */
export function endOfPeriod(date: Dayjs, unit: SpanUnit): Dayjs {
	if (unit === 'week' || unit === 'fiscal year') {
		return shiftPeriods(startOfPeriod(date, unit), unit, 1).subtract(1, 'day')
	}
	return date.endOf(unit as any)
}

/** `date` moved `count` periods of `unit`. */
export function shiftPeriods(date: Dayjs, unit: SpanUnit, count: number): Dayjs {
	if (unit === 'quarter') return date.add(count * 3, 'month')
	// a fiscal year is twelve months long wherever it starts, so it moves by the year
	if (unit === 'fiscal year') return date.add(count, 'year')
	return date.add(count, unit as any)
}
