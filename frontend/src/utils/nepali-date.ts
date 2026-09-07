/**
 * Nepali Bikram Sambat (BS) Calendar Converter
 * Supports AD↔BS conversion for dates from 1970 AD (2026 BS) onwards
 */

// BS year data: each row = [yearBS, days in each of 12 months]
const BS_DATA: Record<number, number[]> = {
  2000: [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2001: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2002: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2003: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2004: [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2005: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2006: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2007: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2008: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31],
  2009: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2010: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2011: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2012: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2013: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2014: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2015: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2016: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2017: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2018: [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2019: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2020: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2021: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2022: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2023: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2024: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2025: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2026: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2027: [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2028: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2029: [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],
  2030: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2031: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2032: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2033: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2034: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2035: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2036: [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],
  2037: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2038: [31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31],
  2039: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2040: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2041: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2042: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2043: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2044: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2045: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2046: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2047: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2048: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2049: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2050: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2051: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2052: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2053: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2054: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2055: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2056: [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],
  2057: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2058: [31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31],
  2059: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2060: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2061: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2062: [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2063: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2064: [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],
  2065: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2066: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2067: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2068: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2069: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],
  2070: [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],
  2071: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2072: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2073: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2074: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2075: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2076: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2077: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2078: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2079: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2080: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2081: [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],
  2082: [32, 31, 32, 31, 31, 30, 30, 30, 29, 29, 30, 30],
  2083: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2084: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2085: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2086: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
  2087: [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],
  2088: [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],
  2089: [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],
  2090: [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],
};

// BS month names
export const BS_MONTHS_NP = [
  "बैशाख", "जेठ", "असार", "श्रावण", "भाद्र", "आश्विन",
  "कार्तिक", "मंसिर", "पुष", "माघ", "फाल्गुन", "चैत्र"
];

export const BS_MONTHS_EN = [
  "Baisakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin",
  "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
];

export const NEPALI_DIGITS = ["०", "१", "२", "३", "४", "५", "६", "७", "८", "९"];

export function toNepaliDigits(n: number | string): string {
  return String(n).replace(/\d/g, (d) => NEPALI_DIGITS[parseInt(d)]);
}

export interface BSDate {
  year: number;
  month: number; // 1-based
  day: number;
}

// Reference: 1st Baisakh 2000 BS = 13th April 1943 AD
const BS_START_YEAR = 2000;
const AD_REF_YEAR = 1943;
const AD_REF_MONTH = 4; // April
const AD_REF_DAY = 14;

function getDaysInBSMonth(year: number, month: number): number {
  const data = BS_DATA[year];
  if (!data) return 30;
  return data[month - 1];
}

function getTotalDaysInBSYear(year: number): number {
  const data = BS_DATA[year];
  if (!data) return 365;
  return data.reduce((a, b) => a + b, 0);
}

/**
 * Convert AD date to BS date
 */
export function adToBS(adDate: Date): BSDate {
  // Days since AD reference date (April 14, 1943)
  const refDate = new Date(AD_REF_YEAR, AD_REF_MONTH - 1, AD_REF_DAY);
  const diffMs = adDate.getTime() - refDate.getTime();
  let totalDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  let bsYear = BS_START_YEAR;
  let bsMonth = 1;
  let bsDay = 1;

  // Walk through BS years
  while (totalDays >= getTotalDaysInBSYear(bsYear)) {
    totalDays -= getTotalDaysInBSYear(bsYear);
    bsYear++;
  }

  // Walk through BS months
  while (totalDays >= getDaysInBSMonth(bsYear, bsMonth)) {
    totalDays -= getDaysInBSMonth(bsYear, bsMonth);
    bsMonth++;
  }

  bsDay = totalDays + 1;

  return { year: bsYear, month: bsMonth, day: bsDay };
}

/**
 * Convert BS date to AD date
 */
export function bsToAD(bs: BSDate): Date {
  let totalDays = 0;

  for (let y = BS_START_YEAR; y < bs.year; y++) {
    totalDays += getTotalDaysInBSYear(y);
  }
  for (let m = 1; m < bs.month; m++) {
    totalDays += getDaysInBSMonth(bs.year, m);
  }
  totalDays += bs.day - 1;

  const refDate = new Date(AD_REF_YEAR, AD_REF_MONTH - 1, AD_REF_DAY);
  const result = new Date(refDate.getTime() + totalDays * 24 * 60 * 60 * 1000);
  return result;
}

/**
 * Format BS date as string
 * @param bs BSDate
 * @param nepaliDigits whether to use Nepali numerals
 * @param long whether to show full month name
 */
export function formatBS(
  bs: BSDate,
  options: { nepaliDigits?: boolean; long?: boolean; english?: boolean } = {}
): string {
  const { nepaliDigits = true, long = true, english = false } = options;
  const monthName = english ? BS_MONTHS_EN[bs.month - 1] : BS_MONTHS_NP[bs.month - 1];
  const day = nepaliDigits ? toNepaliDigits(bs.day) : String(bs.day);
  const year = nepaliDigits ? toNepaliDigits(bs.year) : String(bs.year);

  if (!long) {
    return `${year}/${nepaliDigits ? toNepaliDigits(bs.month) : bs.month}/${day}`;
  }
  return `${day} ${monthName} ${year}`;
}

/**
 * Convert AD date string (YYYY-MM-DD) to formatted BS string
 */
export function adStringToBS(
  adStr: string,
  options: { nepaliDigits?: boolean; long?: boolean; english?: boolean } = {}
): string {
  if (!adStr) return "";
  try {
    const date = new Date(`${adStr}T00:00:00`);
    if (isNaN(date.getTime())) return adStr;
    const bs = adToBS(date);
    return formatBS(bs, options);
  } catch {
    return adStr;
  }
}

/**
 * Get current BS date
 */
export function todayBS(): BSDate {
  return adToBS(new Date());
}

/**
 * Format today as BS string
 */
export function todayBSString(options: { nepaliDigits?: boolean; long?: boolean; english?: boolean } = {}): string {
  return formatBS(todayBS(), options);
}

/**
 * Get full BS date label for display (primary BS, secondary AD)
 * e.g. "१ बैशाख २०८२ (2025-04-14)"
 */
export function fullDateLabel(adStr: string): string {
  if (!adStr) return "";
  const bsStr = adStringToBS(adStr, { nepaliDigits: true, long: true });
  return `${bsStr} (${adStr})`;
}
