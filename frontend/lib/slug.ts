export const slugify = (input: string): string =>
  input
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/æ/g, "ae")
    .replace(/ø/g, "oe")
    .replace(/å/g, "aa")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);

export const isValidSlug = (s: string): boolean =>
  /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(s) && s.length > 0 && s.length <= 64;
