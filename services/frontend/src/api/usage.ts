import { apiGetJson } from "./client";

export interface UsageProviderStats {
  provider: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  total_cost_usd: string;
}

export interface UsagePurposeStats {
  purpose: string;
  calls: number;
  total_cost_usd: string;
}

export interface UsageSummary {
  generated_at: string;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_input_tokens: number;
  total_cost_usd: string;
  avg_latency_ms: number;
  failed_calls: number;
  per_provider: UsageProviderStats[];
  per_purpose: UsagePurposeStats[];
}

export interface UsageCall {
  id: number;
  created_at: string;
  provider: string;
  model: string;
  purpose: string;
  aerodrome_icao: string | null;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  input_cost_usd: string;
  output_cost_usd: string;
  cached_input_cost_usd: string;
  total_cost_usd: string;
  latency_ms: number | null;
  success: boolean;
  error_code: string | null;
}

export function getUsageSummary(): Promise<UsageSummary> {
  return apiGetJson<UsageSummary>("/usage/summary");
}

export function getUsageRecent(limit = 50): Promise<UsageCall[]> {
  return apiGetJson<UsageCall[]>(`/usage/recent?limit=${limit}`);
}
