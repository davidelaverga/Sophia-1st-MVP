"use client";

import { copy } from "../../copy";

export function UsageHint() {
  return (
    <p className="text-center text-xs text-sophia-text2">
      {copy.usageLimit.footerHint}
    </p>
  );
}

