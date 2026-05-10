// Shared-password auth: HMAC-signed session cookie.
//
// Single-user model: one shared password (APP_PASSWORD) gates all writes and
// (per the project's lock-everything decision) all reads too. A successful
// login sets a session cookie containing `<expiresAt>.<HMAC(expiresAt)>`,
// signed with APP_SESSION_SECRET. Both helpers below use Web Crypto so they
// work in Edge (middleware) as well as Node (server actions / RSCs).

export const SESSION_COOKIE = "ss_session";
export const SESSION_TTL_MS = 1000 * 60 * 60 * 24 * 30;

const getSecret = (): string => {
  const s = process.env.APP_SESSION_SECRET;
  if (!s || s.length < 16) {
    throw new Error(
      "APP_SESSION_SECRET must be set and at least 16 characters long",
    );
  }
  return s;
};

const getPassword = (): string => {
  const p = process.env.APP_PASSWORD;
  if (!p) throw new Error("APP_PASSWORD must be set");
  return p;
};

const toBase64Url = (buf: ArrayBuffer): string => {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

const importHmacKey = (secret: string): Promise<CryptoKey> =>
  crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

const sign = async (payload: string, secret: string): Promise<string> => {
  const key = await importHmacKey(secret);
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(payload),
  );
  return toBase64Url(sig);
};

const timingSafeEqual = (a: string, b: string): boolean => {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
};

export const verifyPassword = (input: string): boolean => {
  let expected: string;
  try {
    expected = getPassword();
  } catch {
    return false;
  }
  return timingSafeEqual(input, expected);
};

export const buildSessionToken = async (): Promise<{
  token: string;
  expiresAt: number;
}> => {
  const expiresAt = Date.now() + SESSION_TTL_MS;
  const payload = String(expiresAt);
  const sig = await sign(payload, getSecret());
  return { token: `${payload}.${sig}`, expiresAt };
};

export const verifySessionToken = async (
  token: string | undefined,
): Promise<boolean> => {
  if (!token) return false;
  const dot = token.indexOf(".");
  if (dot <= 0) return false;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expiresAt = Number(payload);
  if (!Number.isFinite(expiresAt) || expiresAt < Date.now()) return false;
  let expected: string;
  try {
    expected = await sign(payload, getSecret());
  } catch {
    return false;
  }
  return timingSafeEqual(expected, sig);
};
