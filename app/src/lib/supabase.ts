type FetchOptions = {
  select: string;
  filters?: string[];
  limit?: number;
  offset?: number;
};

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error("Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables.");
}

const baseUrl = SUPABASE_URL.replace(/\/$/, "") + "/rest/v1";

const headers = {
  apikey: SUPABASE_ANON_KEY,
  Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
  "Content-Type": "application/json",
};

export async function fetchAll<T>(endpoint: string, options: FetchOptions): Promise<T[]> {
  const results: T[] = [];
  const limit = options.limit ?? 1000;
  let offset = options.offset ?? 0;

  while (true) {
    const params = new URLSearchParams();
    params.set("select", options.select);
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (options.filters) {
      for (const filter of options.filters) {
        const [key, ...rest] = filter.split("=");
        const value = rest.join("=");
        params.append(key, value);
      }
    }

    const url = `${baseUrl}/${endpoint}?${params.toString()}`;
    const response = await fetch(url, { headers, next: { revalidate: 3600 } });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Supabase error ${response.status}: ${text}`);
    }
    const batch = (await response.json()) as T[];
    results.push(...batch);
    if (batch.length < limit) {
      break;
    }
    offset += limit;
  }

  return results;
}

export async function fetchOne<T>(endpoint: string, options: FetchOptions): Promise<T | null> {
  const params = new URLSearchParams();
  params.set("select", options.select);
  params.set("limit", "1");
  if (options.filters) {
    for (const filter of options.filters) {
      const [key, ...rest] = filter.split("=");
      const value = rest.join("=");
      params.append(key, value);
    }
  }

  const url = `${baseUrl}/${endpoint}?${params.toString()}`;
  const response = await fetch(url, { headers, next: { revalidate: 3600 } });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase error ${response.status}: ${text}`);
  }
  const data = (await response.json()) as T[];
  return data[0] ?? null;
}
