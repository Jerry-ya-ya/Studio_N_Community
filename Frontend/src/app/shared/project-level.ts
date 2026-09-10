export function toRomanNumeral(value: number | null | undefined): string {
  let remaining = Math.max(1, Math.floor(Number(value) || 1));
  const numerals: Array<[number, string]> = [
    [1000, 'M'],
    [900, 'CM'],
    [500, 'D'],
    [400, 'CD'],
    [100, 'C'],
    [90, 'XC'],
    [50, 'L'],
    [40, 'XL'],
    [10, 'X'],
    [9, 'IX'],
    [5, 'V'],
    [4, 'IV'],
    [1, 'I'],
  ];
  let result = '';

  for (const [numericValue, numeral] of numerals) {
    while (remaining >= numericValue) {
      result += numeral;
      remaining -= numericValue;
    }
  }

  return result;
}
