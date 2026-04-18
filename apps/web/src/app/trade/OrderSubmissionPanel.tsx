"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listAccounts, type ExchangeAccountResponse } from "@/lib/exchange-accounts";
import { placeOrder, type OrderResultResponse, type OrderSide, type OrderType } from "@/lib/orders";

export interface OrderSubmissionPanelProps {
  symbol?: string;
  side?: "buy" | "sell";
  orderType?: "market" | "limit";
  quantity?: string;
  price?: string;
  stopLoss?: string;
  takeProfit?: string;
}

function extractErrorMessage(err: unknown): string {
  if (!(err instanceof Error)) return "Order submission failed";
  const match = err.message.match(/API error \d+: ([\s\S]+)$/);
  if (!match) return err.message;
  try {
    const parsed = JSON.parse(match[1]);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map((e: { msg: string }) => e.msg).join("; ");
    }
  } catch {
    // not JSON
  }
  return match[1];
}

function SummaryRow({ label, sublabel, value }: { label: string; sublabel: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-border/30 py-2 last:border-0">
      <div>
        <span className="text-xs font-light tracking-wide">{label}</span>
        <span className="ml-2 text-[10px] font-light text-muted-foreground">{sublabel}</span>
      </div>
      <span className="font-mono text-sm">{value || "—"}</span>
    </div>
  );
}

export function OrderSubmissionPanel({
  symbol,
  side,
  orderType,
  quantity,
  price,
  stopLoss,
  takeProfit,
}: OrderSubmissionPanelProps) {
  const [accounts, setAccounts] = useState<ExchangeAccountResponse[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<OrderResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAccounts()
      .then((accts) => {
        const active = accts.filter((a) => a.is_active);
        setAccounts(active);
        if (active.length === 1) {
          setSelectedAccountId(active[0].id);
        } else {
          const def = active.find((a) => a.is_default);
          if (def) setSelectedAccountId(def.id);
        }
      })
      .finally(() => setAccountsLoading(false));
  }, []);

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId) ?? null;

  const handleSubmit = useCallback(async () => {
    if (!selectedAccountId) {
      setError("请选择交易账户");
      return;
    }
    if (!symbol || !quantity) {
      setError("缺少必要参数：标的或数量");
      return;
    }
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const res = await placeOrder({
        account_id: selectedAccountId,
        symbol,
        side: (side ?? "buy") as OrderSide,
        order_type: (orderType ?? "market") as OrderType,
        quantity,
        ...(price ? { price } : {}),
        ...(stopLoss ? { stop_loss: stopLoss } : {}),
        ...(takeProfit ? { take_profit: takeProfit } : {}),
      });
      setResult(res);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }, [selectedAccountId, symbol, side, orderType, quantity, price, stopLoss, takeProfit]);

  const hasParams = symbol || quantity;

  return (
    <div className="space-y-4">
      <div>
        <span className="text-xs font-light tracking-wide">下单</span>
        <span className="ml-2 text-[10px] font-light text-muted-foreground">Order Submission</span>
      </div>

      <div className="rounded-md border border-border/50 bg-card p-6 space-y-5">
        {/* Account selector */}
        <div className="space-y-1.5">
          <label className="block">
            <span className="text-xs font-light tracking-wide">交易账户</span>
            <span className="ml-2 text-[10px] font-light text-muted-foreground">Exchange Account</span>
          </label>

          {accountsLoading ? (
            <div className="text-[10px] text-muted-foreground/50">加载中…</div>
          ) : accounts.length === 0 ? (
            <div className="text-[10px] text-muted-foreground/50">
              暂无可用账户，请前往设置添加交易所账户
            </div>
          ) : (
            <select
              value={selectedAccountId}
              onChange={(e) => {
                setSelectedAccountId(e.target.value);
                setResult(null);
                setError(null);
              }}
              className="w-full bg-transparent border border-border rounded-md px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {accounts.length > 1 && <option value="">选择账户…</option>}
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label} · {a.exchange_id.toUpperCase()} · {a.mode}
                </option>
              ))}
            </select>
          )}

          {selectedAccount?.mode === "live" && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2">
              <span className="text-[10px] tracking-widest uppercase text-destructive font-light">
                实盘模式 — 此操作将使用真实资金
              </span>
            </div>
          )}
        </div>

        {/* Order summary */}
        <div className="space-y-0">
          <div className="mb-2 text-[10px] tracking-widest uppercase text-muted-foreground">
            Order Summary
          </div>
          {hasParams ? (
            <div className="space-y-0">
              {symbol && <SummaryRow label="标的" sublabel="Symbol" value={symbol} />}
              {side && (
                <SummaryRow
                  label="方向"
                  sublabel="Side"
                  value={side.toUpperCase()}
                />
              )}
              {orderType && (
                <SummaryRow label="类型" sublabel="Order Type" value={orderType.toUpperCase()} />
              )}
              {quantity && <SummaryRow label="数量" sublabel="Quantity" value={quantity} />}
              {price && <SummaryRow label="价格" sublabel="Price" value={price} />}
              {stopLoss && <SummaryRow label="止损" sublabel="Stop Loss" value={stopLoss} />}
              {takeProfit && <SummaryRow label="止盈" sublabel="Take Profit" value={takeProfit} />}
            </div>
          ) : (
            <div className="py-4 text-center text-xs font-light text-muted-foreground/40">
              请先完成仓位计算
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="rounded-md border border-border/50 bg-muted/20 p-4 space-y-0">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] tracking-widest uppercase text-muted-foreground">
                Order Confirmed
              </span>
              <span
                className={cn(
                  "text-[10px] tracking-widest uppercase border rounded px-1.5 py-0.5",
                  result.status === "filled"
                    ? "border-border/50 text-muted-foreground"
                    : "border-border/50 text-muted-foreground"
                )}
              >
                {result.status}
              </span>
            </div>
            <SummaryRow label="委托号" sublabel="Exchange Order ID" value={result.exchange_order_id} />
            <SummaryRow label="成交量" sublabel="Filled" value={`${result.filled_quantity} / ${result.quantity}`} />
            {result.average_fill_price && (
              <SummaryRow label="成交均价" sublabel="Avg Fill Price" value={result.average_fill_price} />
            )}
            <SummaryRow label="手续费" sublabel="Fee" value={`${result.fee} ${result.fee_currency}`} />
          </div>
        )}

        {/* Submit */}
        <Button
          variant="outline"
          className={cn(
            "w-full",
            selectedAccount?.mode === "live" && "border-destructive/50 text-destructive hover:bg-destructive/10"
          )}
          disabled={submitting || accountsLoading || !selectedAccountId || !hasParams}
          onClick={handleSubmit}
        >
          {submitting
            ? "提交中…"
            : selectedAccount?.mode === "live"
            ? "确认下单（实盘）"
            : "提交订单"}
        </Button>
      </div>
    </div>
  );
}
