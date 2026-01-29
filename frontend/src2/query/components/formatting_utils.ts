import { Column } from "../../types/query.types";

export type ConditionalColor = 'red' | 'amber' | 'green'

export type FormatGroupArgs = {
    formats: FormattingMode[];
    columns: Column[]
}

export type ConditionalOperator =
    | '<'
    | '<='
    | '='
    | '>='
    | '>'
    | '!='

export type TextOperator =
    | 'contains'
    | 'not_contains'
    | 'starts_with'
    | 'ends_with'
    | 'equals_text'
    | 'not_equals_text'
    | 'is_empty'
    | 'is_not_empty'

export type DateOperator =
    | 'is_today'
    | 'is_yesterday'
    | 'is_tomorrow'
    | 'is_this_week'
    | 'is_last_week'
    | 'is_next_week'
    | 'is_this_month'
    | 'is_last_month'
    | 'is_next_month'
    | 'is_this_year'
    | 'is_last_year'
    | 'is_next_year'
    | 'date_between'
    | 'date_before'
    | 'date_after'

export type RankOperator =
    | 'top_n'
    | 'bottom_n'
    | 'top_percent'
    | 'bottom_percent'
    | 'above_average'
    | 'below_average'


export type color_scale = {
    mode: 'color_scale',
    column: Column,
    colorScale?: string,
    scaleScope?: 'global' | 'local',
    value: number | undefined
}

// highlight cell rules
export type cell_rules = {
    mode: 'cell_rules',
    column: Column,
    color?: string,
    operator?: ConditionalOperator,
    value: number | undefined
}

export type text_rules = {
    mode: 'text_rules',
    column: Column,
    color: string,
    operator: TextOperator,
    value: string | undefined
}

export type date_rules = {
    mode: 'date_rules',
    column: Column,
    color: string,
    operator: DateOperator,
    value?: string | Date | [Date, Date] | undefined
}

export type rank_rules = {
    mode: 'rank_rules',
    column: Column,
    color: string,
    operator: RankOperator,
    value: number | undefined
}

// rule and color scale based coloring of cell
export type FormattingMode = color_scale | cell_rules | text_rules | date_rules | rank_rules

// color scale options Red-Amber-Green and Green-Amber-Red
export const ragByPercentage = {
    10: "bg-[#d87373] text-white",
    20: "bg-[#e29696] text-black",
    30: "bg-[#ebb9b9] text-black",
    40: "bg-[#EFC5C5] text-black",
    50: "bg-[#FBECEC] text-black",
    60: "bg-[#EEF7EF] text-black",
    70: "bg-[#CEE7D3] text-black",
    80: "bg-[#c5e2c9] text-black",
    90: "bg-[#a7d3ae] text-black",
    100: "bg-[#8ac593] text-white",
};

export const garByPercentage = {
    10: "bg-[#8AC593] text-white",
    20: "bg-[#A7D3AE] text-black",
    30: "bg-[#C5E2C9] text-black",
    40: "bg-[#CEE7D3] text-black",
    50: "bg-[#EEF7EF] text-black",
    60: "bg-[#FBECEC] text-black",
    70: "bg-[#EFC5C5] text-black",
    80: "bg-[#EBB9B9] text-black",
    90: "bg-[#E29696] text-black",
    100: "bg-[#D87373] text-white",
};

// helper functions for date comparison
function isSameDay(date1: Date, date2: Date): boolean {
    return date1.getDate() === date2.getDate() &&
        date1.getMonth() === date2.getMonth() &&
        date1.getFullYear() === date2.getFullYear();
}

function isSameWeek(date1: Date, date2: Date): boolean {
    const week1 = getWeekNumber(date1);
    const week2 = getWeekNumber(date2);
    return week1.week === week2.week && week1.year === week2.year;
}

function getWeekNumber(date: Date): { week: number, year: number } {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + 4 - (d.getDay() || 7));
    const yearStart = new Date(d.getFullYear(), 0, 1);
    const weekNumber = Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
    return { week: weekNumber, year: d.getFullYear() };
}

//convert the given input to number
export function useNumber(num: any) {
    const valueStr = String(num);
    const cleanVal = valueStr.replace(/,|\s/g, '');
    const result = parseFloat(cleanVal);
    if (isNaN(result)) {
        return null;
    }
    return result;
}

export function applyRule(
    value: any,
    rule: cell_rules
) {

    const numberVal = useNumber(value)
    if (numberVal === null) return;
    switch (rule.operator) {
        case '<':
            return numberVal < (rule.value as number)
        case '<=':
            return numberVal <= (rule.value as number)
        case '=':
            return numberVal === (rule.value as number)
        case '>':
            return numberVal > (rule.value as number)
        case '>=':
            return numberVal >= (rule.value as number)
        case '!=':
            return numberVal !== (rule.value)
    }

}

export function applyTextRule(
    value: any,
    rule: text_rules
): boolean {
    const textVal = String(value).toLowerCase();
    const ruleValue = String(rule.value || '').toLowerCase();

    switch (rule.operator) {
        case 'contains':
            return textVal.includes(ruleValue);
        case 'not_contains':
            return !textVal.includes(ruleValue);
        case 'starts_with':
            return textVal.startsWith(ruleValue);
        case 'ends_with':
            return textVal.endsWith(ruleValue);
        case 'equals_text':
            return textVal === ruleValue;
        case 'not_equals_text':
            return textVal !== ruleValue;
        case 'is_empty':
            return textVal.trim() === '';
        case 'is_not_empty':
            // handle null case as well
            return textVal.trim() !== '' || ruleValue.trim() !== null;
        default:
            return false;
    }
}

export function applyDateRule(
    value: any,
    rule: date_rules
): boolean {
    const dateVal = new Date(value);
    if (isNaN(dateVal.getTime())) return false;

    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    switch (rule.operator) {
        case 'is_today':
            return isSameDay(dateVal, today);
        case 'is_yesterday':
            return isSameDay(dateVal, yesterday);
        case 'is_tomorrow':
            return isSameDay(dateVal, tomorrow);
        case 'is_this_week':
            return isSameWeek(dateVal, today);
        case 'is_last_week':
            const lastWeek = new Date(today);
            lastWeek.setDate(today.getDate() - 7);
            return isSameWeek(dateVal, lastWeek);
        case 'is_next_week':
            const nextWeek = new Date(today);
            nextWeek.setDate(today.getDate() + 7);
            return isSameWeek(dateVal, nextWeek);
        case 'is_this_month':
            return dateVal.getMonth() === today.getMonth() && dateVal.getFullYear() === today.getFullYear();
        case 'is_last_month':
            const lastMonth = new Date(today);
            lastMonth.setMonth(today.getMonth() - 1);
            return dateVal.getMonth() === lastMonth.getMonth() && dateVal.getFullYear() === lastMonth.getFullYear();
        case 'is_next_month':
            const nextMonth = new Date(today);
            nextMonth.setMonth(today.getMonth() + 1);
            return dateVal.getMonth() === nextMonth.getMonth() && dateVal.getFullYear() === nextMonth.getFullYear();
        case 'is_this_year':
            return dateVal.getFullYear() === today.getFullYear();
        case 'is_last_year':
            return dateVal.getFullYear() === today.getFullYear() - 1;
        case 'is_next_year':
            return dateVal.getFullYear() === today.getFullYear() + 1;
        case 'date_between':
            if (Array.isArray(rule.value) && rule.value.length === 2) {
                const [start, end] = rule.value.map(date => new Date(date));
                return dateVal >= start && dateVal <= end;
            }
            return false;
        case 'date_before':
            const beforeDate = new Date(rule.value as string);
            return dateVal < beforeDate;
        case 'date_after':
            const afterDate = new Date(rule.value as string);
            return dateVal > afterDate;
        default:
            return false;
    }
}

export function applyRankRule(
    value: any,
    rule: rank_rules,
    allValues: number[]
): boolean {
    const numVal = useNumber(value);
    if (numVal === null) return false;
    // sort descending
    const numericValues = allValues
        .sort((a, b) => b - a);

    if (numericValues.length === 0) return false;

    const n = rule.value || 0;
    const average = numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length;
    // todo: use custom expression
    switch (rule.operator) {
        case 'top_n':
            return numericValues.slice(0, n).includes(numVal);
        case 'bottom_n':
            return numericValues.slice(-n).includes(numVal);
        case 'top_percent':
            const topCount = Math.ceil((n / 100) * numericValues.length);
            return numericValues.slice(0, topCount).includes(numVal);
        case 'bottom_percent':
            const bottomCount = Math.ceil((n / 100) * numericValues.length);
            return numericValues.slice(-bottomCount).includes(numVal);
        case 'above_average':
            return numVal > average;
        case 'below_average':
            return numVal < average;
        default:
            return false;
    }
}
