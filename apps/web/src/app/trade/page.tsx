"use client";

import { useState } from "react";
import { PositionSizingCalculator, type CalculatorResult } from "./PositionSizingCalculator";
import { OrderSubmissionPanel } from "./OrderSubmissionPanel";

export default function TradePage() {
  const [orderParams, setOrderParams] = useState<CalculatorResult | null>(null);

  return (
    <div className="space-y-8">
      <PositionSizingCalculator onResult={setOrderParams} />
      <div className="border-t border-border/30" />
      <OrderSubmissionPanel
        symbol={orderParams?.symbol}
        side={orderParams?.side}
        orderType="market"
        quantity={orderParams?.quantity}
        price={orderParams?.price}
        stopLoss={orderParams?.stopLoss}
        takeProfit={orderParams?.takeProfit}
      />
    </div>
  );
}
