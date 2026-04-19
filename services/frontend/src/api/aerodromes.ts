import { apiGetJson, apiListJson, type ApiListResponse } from "./client";

export type AerodromeType =
  | "international"
  | "regional"
  | "general_aviation"
  | "military"
  | "private"
  | "other";

export type FrequencyType =
  | "twr"
  | "gnd"
  | "atis"
  | "afis"
  | "app"
  | "dep"
  | "del"
  | "info"
  | "radio"
  | "cta"
  | "fis"
  | "emergency"
  | "other";

export type RunwaySurface =
  | "asphalt"
  | "concrete"
  | "grass"
  | "gravel"
  | "sand"
  | "water"
  | "snow"
  | "other";

export interface Aerodrome {
  icao: string;
  iata: string | null;
  name: string;
  name_de: string | null;
  city: string | null;
  city_de: string | null;
  region: string | null;
  region_de: string | null;
  country: string;
  type: AerodromeType;
  latitude: number | null;
  longitude: number | null;
  elevation_ft: number | null;
  source_airac_cycle: string | null;
  created_at: string;
  updated_at: string;
}

export interface Runway {
  id: number;
  designator_le: string;
  designator_he: string;
  length_m: number | null;
  width_m: number | null;
  surface: RunwaySurface;
  ils_le: boolean;
  ils_he: boolean;
}

export interface Frequency {
  id: number;
  type: FrequencyType;
  callsign: string | null;
  callsign_de: string | null;
  frequency_mhz: string; // Pydantic serializes Decimal as string
}

export interface Chart {
  id: number;
  chart_type: string;
  title: string;
  title_de: string | null;
  source_url: string;
}

export interface Notam {
  id: number;
  notam_id: string;
  severity: "critical" | "high" | "normal" | "low";
  b_valid_from: string;
  c_valid_to: string | null;
  e_condition: string;
  e_condition_de: string | null;
}

export interface AerodromeDetail extends Aerodrome {
  runways: Runway[];
  frequencies: Frequency[];
  charts: Chart[];
  notams: Notam[];
}

export interface ListParams {
  q?: string;
  type?: AerodromeType;
  region?: string;
  limit?: number;
  offset?: number;
}

export function listAerodromes(
  params: ListParams,
): Promise<ApiListResponse<Aerodrome>> {
  return apiListJson<Aerodrome>("/aerodromes", { ...params });
}

export function getAerodrome(icao: string): Promise<AerodromeDetail> {
  return apiGetJson<AerodromeDetail>(`/aerodromes/${icao}`);
}
