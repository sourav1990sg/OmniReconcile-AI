/**
 * BusinessIntelligenceReport types — mirrors backend/intelligence/models.py.
 * Dashboard decision UI renders BI only; analytics KPIs come from bi.analytics passthrough.
 */

import type { AnalyticsReport } from "@/components/intelligence/analytics-types";

export type Severity = "Low" | "Medium" | "High" | "Critical";

export interface IntelligenceCard {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  business_impact: string;
  recommended_action: string;
  supporting_metrics: Record<string, string | number | boolean | null>;
  confidence: number;
  category?: string;
  domain?: string;
}

export interface PriorityAction {
  rank: number;
  title: string;
  description: string;
  severity: Severity;
  recommended_action: string;
  business_impact: string;
  owner: string;
  confidence: number;
  source_card_ids: string[];
  supporting_metrics: Record<string, string | number | boolean | null>;
}

export interface ExecutiveDecisionSummary {
  headline: string;
  situation: string;
  primary_risk: string;
  primary_opportunity: string;
  next_action: string;
  risk_count: number;
  opportunity_count: number;
  high_priority_count: number;
  online_sales: number;
  platform_payout: number;
  recoverable_amount: number;
  settlement_coverage_pct: number;
  agreement_violations: number;
}

export interface BusinessIntelligenceReport {
  executive_summary: ExecutiveDecisionSummary;
  financial_risks: IntelligenceCard[];
  commercial_risks: IntelligenceCard[];
  operations_risks: IntelligenceCard[];
  recovery_opportunities: IntelligenceCard[];
  outlet_opportunities: IntelligenceCard[];
  platform_opportunities: IntelligenceCard[];
  priority_actions: PriorityAction[];
  insight_cards: IntelligenceCard[];
  recommendation_cards: IntelligenceCard[];
  risk_cards: IntelligenceCard[];
  opportunity_cards: IntelligenceCard[];
  /** AnalyticsReport passthrough — KPIs/charts only; never recalculate. */
  analytics: AnalyticsReport;
}
