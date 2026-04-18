"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  calculatePosition,
  type MarketType,
  type PositionCalculateResponse,
  type TradeSide,
} from "@/lib/position-sizing";

interface FormState {
  symbol: string;
  account_equity: string;
  risk_percent: string;
  entry_price: string;
  stop_price: string;
  side: TradeSide;
  market_type: MarketType;
  leverage: string;
  fee_rate: string;
  take_profit_price: string;
}

const initialForm: FormState = {
  symbol: "",
  account_equity: "",
  risk_percent: "1",
  entry_price: "",
  stop_price: "",
  side: "long",
  market_type: "spot",
  leverage: "1",
  fee_rate: "",
  take_profit_price: "",
};

export interface CalculatorResult {
  symbol: string;
  side: "buy" | "sell";
  quantity: string;
  price: string;
  stopLoss: string;
  takeProfit: string;
}

interface PositionSizingCalculatorProps {
  onResult?: (result: CalculatorResult | null) => void;
}

function extractErrorMessage(rawError: string): string {
  const match = rawError.match(/API error \d+: ([\s\S]+)$/);
  if (!match) return rawError;
  try {
    const parsed = JSON.parse(match[1]);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((e: { msg: string }) => e.msg)
        .join("; ");
    }
  } catch {
    // not JSON
  }
  return match[1];
}

function normalizeDecimalInput(value: string): string {
  return value.replace(/,/g, ".");
}

const inputClasses =
  "w-full bg-transparent border border-border rounded-md px-3 py-1.5 text-sm font-mono placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-ring";

interface FieldProps {
  label: string;
  sublabel: string;
  name: keyof FormState;
  placeholder?: string;
  value: string;
  onChange: (name: keyof FormState, value: string) => void;
}

function Field({
  label,
  sublabel,
  name,
  placeholder,
  value,
  onChange,
}: FieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="block">
        <span className="text-xs font-light tracking-wide">{label}</span>
        <span className="ml-2 text-[10px] font-light text-muted-foreground">
          {sublabel}
        </span>
      </label>
      <input
        type="text"
        inputMode="decimal"
        name={name}
        value={value}
        placeholder={placeholder}
        onChange={(e) =>
          onChange(name, normalizeDecimalInput(e.target.value))
        }
        className={inputClasses}
      />
    </div>
  );
}

interface ToggleGroupProps<T extends string> {
  label: string;
  sublabel: string;
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
}

function ToggleGroup<T extends string>({
  label,
  sublabel,
  options,
  value,
  onChange,
}: ToggleGroupProps<T>) {
  return (
    <div className="space-y-1.5">
      <div>
        <span className="text-xs font-light tracking-wide">{label}</span>
        <span className="ml-2 text-[10px] font-light text-muted-foreground">
          {sublabel}
        </span>
      </div>
      <div className="flex overflow-hidden rounded-md border border-border">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={cn(
              "flex-1 py-1.5 text-[10px] tracking-widest uppercase transition-colors",
              value === opt
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

const resultFields: {
  key: keyof PositionCalculateResponse;
  label: string;
  sublabel: string;
}[] = [
  { key: "position_size", label: "仓位大小", sublabel: "Position Size" },
  { key: "risk_amount", label: "风险金额", sublabel: "Risk Amount" },
  {
    key: "reward_risk_ratio",
    label: "盈亏比",
    sublabel: "Reward / Risk",
  },
  {
    key: "stop_distance_percent",
    label: "止损距离",
    sublabel: "Stop Distance %",
  },
  { key: "notional_value", label: "名义价值", sublabel: "Notional Value" },
  {
    key: "margin_required",
    label: "所需保证金",
    sublabel: "Margin Required",
  },
  { key: "fee_estimate", label: "预估手续费", sublabel: "Fee Estimate" },
];

export function PositionSizingCalculator({ onResult }: PositionSizingCalculatorProps) {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<PositionCalculateResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function updateField(name: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const required = [
      ["account_equity", "账户权益"],
      ["risk_percent", "风险比例"],
      ["entry_price", "入场价"],
      ["stop_price", "止损价"],
    ] as const;
    for (const [key, label] of required) {
      if (!form[key].trim()) {
        setError(`${label} 不能为空`);
        return;
      }
    }

    setLoading(true);
    try {
      const res = await calculatePosition({
        account_equity: form.account_equity,
        risk_percent: form.risk_percent,
        entry_price: form.entry_price,
        stop_price: form.stop_price,
        side: form.side,
        market_type: form.market_type,
        ...(form.market_type === "perpetual" && {
          leverage: form.leverage,
        }),
        ...(form.fee_rate.trim() !== "" && { fee_rate: form.fee_rate }),
        ...(form.take_profit_price.trim() !== "" && {
          take_profit_price: form.take_profit_price,
        }),
      });
      setResult(res);
      onResult?.({
        symbol: form.symbol.trim(),
        side: form.side === "long" ? "buy" : "sell",
        quantity: res.position_size,
        price: form.entry_price,
        stopLoss: form.stop_price,
        takeProfit: form.take_profit_price,
      });
    } catch (err: unknown) {
      setResult(null);
      onResult?.(null);
      setError(
        extractErrorMessage(
          err instanceof Error ? err.message : "Calculation failed",
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-light tracking-wide">仓位计算</h1>
        <p className="mt-1 text-xs font-light text-muted-foreground">
          Position Sizing Calculator
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Input form */}
        <section className="rounded-md border border-border/50 bg-card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field
              label="标的"
              sublabel="Symbol"
              name="symbol"
              placeholder="BTC/USDT"
              value={form.symbol}
              onChange={updateField}
            />

            <div className="grid grid-cols-2 gap-4">
              <ToggleGroup
                label="方向"
                sublabel="Side"
                options={["long", "short"] as const}
                value={form.side}
                onChange={(v) => updateField("side", v)}
              />
              <ToggleGroup
                label="市场"
                sublabel="Market"
                options={["spot", "perpetual"] as const}
                value={form.market_type}
                onChange={(v) => updateField("market_type", v)}
              />
            </div>

            <Field
              label="账户权益"
              sublabel="Account Equity"
              name="account_equity"
              placeholder="10000"
              value={form.account_equity}
              onChange={updateField}
            />
            <Field
              label="风险比例 %"
              sublabel="Risk Percent"
              name="risk_percent"
              placeholder="1"
              value={form.risk_percent}
              onChange={updateField}
            />

            <div className="grid grid-cols-2 gap-4">
              <Field
                label="入场价"
                sublabel="Entry Price"
                name="entry_price"
                placeholder="65000"
                value={form.entry_price}
                onChange={updateField}
              />
              <Field
                label="止损价"
                sublabel="Stop Price"
                name="stop_price"
                placeholder="63000"
                value={form.stop_price}
                onChange={updateField}
              />
            </div>

            {form.market_type === "perpetual" && (
              <Field
                label="杠杆倍数"
                sublabel="Leverage"
                name="leverage"
                placeholder="1"
                value={form.leverage}
                onChange={updateField}
              />
            )}

            <div className="grid grid-cols-2 gap-4">
              <Field
                label="手续费率"
                sublabel="Fee Rate"
                name="fee_rate"
                placeholder="0.001"
                value={form.fee_rate}
                onChange={updateField}
              />
              <Field
                label="止盈价"
                sublabel="Take Profit"
                name="take_profit_price"
                placeholder=""
                value={form.take_profit_price}
                onChange={updateField}
              />
            </div>

            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="outline"
              className="w-full"
              disabled={loading}
            >
              {loading ? "计算中…" : "计算仓位"}
            </Button>
          </form>
        </section>

        {/* Results */}
        <section className="rounded-md border border-border/50 bg-card p-6">
          {result ? (
            <div className="space-y-0">
              <div className="mb-4 flex items-baseline justify-between">
                <span className="text-xs font-light tracking-wide text-muted-foreground">
                  计算结果
                </span>
                <span className="text-[10px] tracking-widest uppercase text-muted-foreground">
                  {result.side} · {result.market_type}
                </span>
              </div>
              {resultFields.map(({ key, label, sublabel }) => {
                const raw = result[key];
                const value =
                  raw === null || raw === undefined ? "—" : String(raw);
                return (
                  <div
                    key={key}
                    className="flex items-baseline justify-between border-b border-border/30 py-2.5 last:border-0"
                  >
                    <div>
                      <span className="text-xs font-light tracking-wide">
                        {label}
                      </span>
                      <span className="ml-2 text-[10px] font-light text-muted-foreground">
                        {sublabel}
                      </span>
                    </div>
                    <span className="font-mono text-sm">{value}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex h-full min-h-[200px] items-center justify-center">
              <p className="text-xs font-light text-muted-foreground/50">
                填写参数后点击计算
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
