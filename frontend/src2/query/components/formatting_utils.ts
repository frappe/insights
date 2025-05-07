import { Column } from "../../types/query.types";

// [todo]: add ability to select from colorpicker
export type ConditionalColor = 'red' | 'amber' | 'green' 

export type FormatGroupArgs = {
    formats: FormattingMode[];
	columns?: string[]
}

export type ConditionalOperator =
    | '<'
    | '<='
    | '='
    | '>='
    | '>'
    | '!='

    export type ColorByPercentage = {
        0: string,
        10:string,
        40: string,
        70: string,
        90: string,
        100: string,
    };
    
    export type color_scale = {
        mode: 'color_scale',
        column: Column ,
        colorScale?: string,
        value: number | any[] |undefined 
       
    }

    // highlight cell rules
    export type cell_rules ={
        mode: 'cell_rules',
        column: Column ,
        color: string,
        operator: ConditionalOperator,
        value: number | any[] |undefined
    }

    // rule and color scale based coloring of cell 
export type FormattingMode = color_scale| cell_rules


// color scale options Red-Amber-Green and Green-Amber-Red
export const ragByPercentage = {
    0: "bg-[#EB4D52] text-white",
   10: "bg-[#FA8A40] text-black", 
  40: "bg-[#F0BA31] text-black",
  70: "bg-[#F9E8A5] text-black",
  90: "bg-[#C8F3DE] text-black",
  100: "bg-[#78D7A9] text-black",
}

export const garByPercentage ={
	0: "bg-[#78D7A9] text-black",
    10: "bg-[#C8F3DE] text-black",
	40: "bg-[#F9E8A5] text-black",
	70: "bg-[#F0BA31] text-black",
	90: "bg-[#FA8A40] text-black",	
    100: "bg-[#EB4D52] text-white"
}

//convert the given input to number
export function useNumber(val:any) {
    const valueStr = String(val);
    const cleanValue = valueStr.replace(/,|\s/g, '');
    const result = parseFloat(cleanValue);
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
    if(numberVal === null) return;
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


