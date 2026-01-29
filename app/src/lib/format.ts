export function formatPrice(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return "Price varies";
  }
  const rounded = Math.round(value);
  return `$${rounded}`;
}

export function formatPriceRange(min: number | null, max: number | null): string {
  if (min === null || max === null || Number.isNaN(min) || Number.isNaN(max)) {
    return "Price varies";
  }
  const roundedMin = Math.round(min);
  const roundedMax = Math.round(max);
  if (roundedMin === roundedMax) {
    return `$${roundedMin}`;
  }
  return `$${roundedMin} - $${roundedMax}`;
}

const MENU_TYPE_RULES = [
  { match: /brunch/i, label: "Brunch" },
  { match: /lunch/i, label: "Lunch" },
  { match: /dinner/i, label: "Dinner" },
  { match: /breakfast/i, label: "Breakfast" },
  { match: /take\s*out|to\s*go|togo/i, label: "Takeout" },
  { match: /special/i, label: "Special" },
];

export function normalizeMenuType(title: string): string {
  for (const rule of MENU_TYPE_RULES) {
    if (rule.match.test(title)) {
      return rule.label;
    }
  }
  return title.split(" ")[0] || "Menu";
}
