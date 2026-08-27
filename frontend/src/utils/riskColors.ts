import type { RiskLevel } from "../types/api";

// Fixed mapping, not a hash: risk levels are a known small enum (unlike
// clause categories), so each one gets an intentional, consistent color.
const RISK_COLORS: Record<RiskLevel, string> = {
  HIGH: "#dc2626",
  MEDIUM: "#d4af6a", // == --gold
  INFORMATIONAL: "#6366f1", // == --accent
};

export function colorForRiskLevel(level: RiskLevel): string {
  return RISK_COLORS[level];
}
