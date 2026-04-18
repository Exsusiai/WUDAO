import { api } from "@/lib/api";

// ---------------------------------------------------------------------------
// Enums mirroring the backend domain types
// ---------------------------------------------------------------------------

export type OrderSide = "buy" | "sell";
export type OrderType = "market" | "limit";
export type OrderStatus =
  | "pending"
  | "open"
  | "partially_filled"
  | "filled"
  | "cancelled"
  | "rejected"
  | "expired";

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface OrderResultResponse {
  exchange_order_id: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  status: OrderStatus;
  /** Fixed-point decimal string, e.g. "0.001" */
  quantity: string;
  filled_quantity: string;
  price: string | null;
  average_fill_price: string | null;
  fee: string;
  fee_currency: string;
  created_at: string;
  updated_at: string;
}

export interface BalanceItemResponse {
  currency: string;
  total: string;
  free: string;
  used: string;
}

export interface AccountBalanceResponse {
  balances: BalanceItemResponse[];
  timestamp: string;
}

export interface PositionResponse {
  symbol: string;
  side: OrderSide;
  quantity: string;
  entry_price: string;
  mark_price: string | null;
  unrealized_pnl: string | null;
  leverage: string;
  liquidation_price: string | null;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface PlaceOrderRequest {
  account_id: string;
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: string;
  price?: string;
  stop_loss?: string;
  take_profit?: string;
  client_order_id?: string;
}

// ---------------------------------------------------------------------------
// API client functions
// ---------------------------------------------------------------------------

export function placeOrder(req: PlaceOrderRequest): Promise<OrderResultResponse> {
  return api.post<OrderResultResponse>("/api/orders", req);
}

export function cancelOrder(
  exchangeOrderId: string,
  accountId: string,
  symbol: string
): Promise<OrderResultResponse> {
  const params = new URLSearchParams({ account_id: accountId, symbol });
  return api.delete<OrderResultResponse>(`/api/orders/${exchangeOrderId}?${params}`);
}

export function getOrder(
  exchangeOrderId: string,
  accountId: string,
  symbol: string
): Promise<OrderResultResponse> {
  const params = new URLSearchParams({ account_id: accountId, symbol });
  return api.get<OrderResultResponse>(`/api/orders/${exchangeOrderId}?${params}`);
}

export function listOpenOrders(
  accountId: string,
  symbol?: string
): Promise<OrderResultResponse[]> {
  const params = new URLSearchParams({ account_id: accountId });
  if (symbol) params.set("symbol", symbol);
  return api.get<OrderResultResponse[]>(`/api/orders?${params}`);
}

export function getBalance(accountId: string): Promise<AccountBalanceResponse> {
  const params = new URLSearchParams({ account_id: accountId });
  return api.get<AccountBalanceResponse>(`/api/orders/balance?${params}`);
}

export function getPositions(
  accountId: string,
  symbol?: string
): Promise<PositionResponse[]> {
  const params = new URLSearchParams({ account_id: accountId });
  if (symbol) params.set("symbol", symbol);
  return api.get<PositionResponse[]>(`/api/orders/positions?${params}`);
}
