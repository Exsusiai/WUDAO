import { api } from "@/lib/api";

export type TradeSide = "long" | "short";
export type MarketType = "spot" | "perpetual";

export interface PositionCalculateRequest {
  account_equity: string;
  risk_percent: string;
  entry_price: string;
  stop_price: string;
  side: TradeSide;
  market_type: MarketType;
  leverage?: string;
  fee_rate?: string;
  take_profit_price?: string;
}

export interface PositionCalculateResponse {
  position_size: string;
  risk_amount: string;
  reward_risk_ratio: string | null;
  stop_distance_percent: string;
  stop_price: string;
  notional_value: string;
  margin_required: string;
  fee_estimate: string;
  market_type: MarketType;
  side: TradeSide;
}

export function calculatePosition(
  req: PositionCalculateRequest,
): Promise<PositionCalculateResponse> {
  return api.post<PositionCalculateResponse>(
    "/api/position/calculate",
    req,
  );
}
