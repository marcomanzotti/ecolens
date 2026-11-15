import { buildPlaceIndex, type PlaceIndexFile, type WorldPlace } from "@/lib/place-search";

/** Every city above 15,000 inhabitants (GeoNames, CC BY 4.0), about 0.5 MB compressed. */
const PLACE_INDEX_URL = "/places/cities.json";

let pending: Promise<readonly WorldPlace[]> | null = null;

function isIndexFile(value: unknown): value is PlaceIndexFile {
  if (typeof value !== "object" || value === null) return false;
  const file = value as Partial<PlaceIndexFile>;
  return Array.isArray(file.places) && typeof file.countries === "object" && file.countries !== null;
}

async function fetchIndex(): Promise<readonly WorldPlace[]> {
  const response = await fetch(PLACE_INDEX_URL);
  if (!response.ok) throw new Error(`The list of places could not be loaded (HTTP ${response.status}).`);
  const body: unknown = await response.json();
  if (!isIndexFile(body)) throw new Error("The list of places is not in the expected format.");
  return buildPlaceIndex(body);
}

/** Fetched once, on the first search; a failed load can be retried. */
export function loadWorldPlaces(): Promise<readonly WorldPlace[]> {
  if (!pending) {
    pending = fetchIndex().catch((error: unknown) => {
      pending = null;
      throw error;
    });
  }
  return pending;
}
