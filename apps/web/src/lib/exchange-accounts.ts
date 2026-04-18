import { api } from "@/lib/api";

export interface ExchangeAccountResponse {
  id: string;
  label: string;
  exchange_id: string;
  mode: string;
  is_default: boolean;
  is_active: boolean;
  has_passphrase: boolean;
  api_key_hint: string;
  created_at: string;
  updated_at: string;
}

export interface CreateExchangeAccountRequest {
  label: string;
  exchange_id: string;
  api_key: string;
  api_secret: string;
  passphrase?: string;
  mode?: string;
  is_default?: boolean;
}

export interface UpdateExchangeAccountRequest {
  label?: string;
  api_key?: string;
  api_secret?: string;
  passphrase?: string;
  mode?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export function listAccounts(): Promise<ExchangeAccountResponse[]> {
  return api.get<ExchangeAccountResponse[]>("/api/exchange-accounts");
}

export function getSupportedExchanges(): Promise<string[]> {
  return api.get<string[]>("/api/exchange-accounts/supported-exchanges");
}

export function createAccount(
  req: CreateExchangeAccountRequest
): Promise<ExchangeAccountResponse> {
  return api.post<ExchangeAccountResponse>("/api/exchange-accounts", req);
}

export function updateAccount(
  id: string,
  req: UpdateExchangeAccountRequest
): Promise<ExchangeAccountResponse> {
  return api.put<ExchangeAccountResponse>(
    `/api/exchange-accounts/${id}`,
    req
  );
}

export function deleteAccount(id: string): Promise<void> {
  return api.delete<void>(`/api/exchange-accounts/${id}`);
}
