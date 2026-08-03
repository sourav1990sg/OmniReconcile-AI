"""Zomato settlement financial engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from backend.platform_engines.base_engine import PlatformFinancialEngine
from backend.platform_engines.column_utils import find_column, money, pick_money, present_components
from backend.platform_engines.models import FinancialBreakdown, FinancialStatus


class ZomatoFinancialEngine(PlatformFinancialEngine):
    """
    Explain Zomato Order Level Payout from settlement components.

    Primary formula (column-name driven):
        calculated_payout = Net Order Value − Net Deductions + Net Additions

    Falls back to summing detected fee/tax/deduction lines when rollups absent.
    """

    @property
    def platform(self) -> str:
        return "zomato"

    def compute(
        self,
        *,
        order_id: str,
        settlement_row: Mapping[str, Any],
        actual_payout: Decimal | None,
        pos_sale: Decimal | None = None,
        tolerance: Decimal = Decimal("0.01"),
    ) -> FinancialBreakdown:
        cols = [str(c) for c in settlement_row.keys()]
        q = Decimal("0.01")

        net_order = pick_money(
            settlement_row,
            cols,
            ("net order value", "net order value [", "commissionable value"),
        )
        # Prefer explicit Net order value over commissionable when both match poorly
        nov_col = find_column(cols, ("net order value",))
        if nov_col:
            net_order = money(settlement_row.get(nov_col))

        commissionable = pick_money(settlement_row, cols, ("commissionable value", "total commissionable"))
        service_fee = pick_money(settlement_row, cols, ("service fee", "base service fee"))
        # Avoid capturing "service fees %" — prefer fee amount columns
        fee_col = find_column(cols, ("service fee\n", "service fee [", "base service fee"))
        if fee_col and "%" not in fee_col.lower():
            service_fee = money(settlement_row.get(fee_col))
        else:
            # scan for Service fee without %
            for c in cols:
                n = c.lower()
                if "service fee" in n and "%" not in n and "payment" not in n and "taxes" not in n:
                    if "fees %" in n or n.strip().endswith("%"):
                        continue
                    service_fee = money(settlement_row.get(c))
                    break

        payment_fee = pick_money(settlement_row, cols, ("payment mechanism fee",))
        taxes_on_fees = pick_money(
            settlement_row,
            cols,
            ("taxes on service", "taxes on service & payment"),
        )
        tcs = pick_money(settlement_row, cols, ("tax collected at source", "tcs igst", "tcs"))
        tds = pick_money(settlement_row, cols, ("tds 194o", "tds"))
        gst_95 = pick_money(
            settlement_row,
            cols,
            (
                "gst paid by zomato on behalf of restaurant under section 9(5)",
                "gst paid by zomato on behalf of restaurant",
                "gst under section 9(5)",
            ),
        )
        gov_charges = pick_money(settlement_row, cols, ("government charges",))
        customer_comp = pick_money(settlement_row, cols, ("customer compensation", "customer compensation/recoupment"))
        delivery_recovery = pick_money(settlement_row, cols, ("delivery charges recovery",))
        promo = pick_money(settlement_row, cols, ("promo recovery",))
        ads = pick_money(settlement_row, cols, ("extra inventory ads", "ads and misc"))
        loyalty = pick_money(settlement_row, cols, ("brand loyalty",))
        brand_pack = pick_money(settlement_row, cols, ("brand pack subscription",))
        express = pick_money(settlement_row, cols, ("express order fee",))
        packaging = pick_money(settlement_row, cols, ("packaging charge",))
        delivery_fee = pick_money(
            settlement_row,
            cols,
            ("delivery charge for restaurants", "delivery charge discount"),
        )
        other_ded_line = pick_money(settlement_row, cols, ("other order-level deductions",))
        net_deductions = pick_money(settlement_row, cols, ("net deductions",))
        net_additions = pick_money(settlement_row, cols, ("net additions",))
        subtotal = pick_money(settlement_row, cols, ("subtotal (items total)", "subtotal"))

        payout_col = find_column(
            cols,
            ("order level payout", "order level payout\n", "net payout"),
        )
        reported_payout = money(settlement_row.get(payout_col)) if payout_col else Decimal("0")
        actual = (actual_payout if actual_payout is not None else reported_payout).quantize(q)

        formula = "Net Order Value − Net Deductions + Net Additions"
        if nov_col and find_column(cols, ("net deductions",)):
            calculated = (net_order - net_deductions + net_additions).quantize(q)
        else:
            # Component fallback
            formula = "Gross components − fees − taxes − other deductions + additions"
            gross = net_order if net_order else (commissionable if commissionable else subtotal)
            deducted = (
                service_fee
                + payment_fee
                + taxes_on_fees
                + tcs
                + tds
                + gov_charges
                + customer_comp
                + delivery_recovery
                + promo
                + ads
                + loyalty
                + brand_pack
                + express
                + other_ded_line
            )
            calculated = (gross - deducted + net_additions).quantize(q)

        total_deductions = (
            net_deductions
            if net_deductions
            else (
                service_fee
                + payment_fee
                + taxes_on_fees
                + tcs
                + tds
                + gov_charges
                + customer_comp
                + promo
                + ads
                + loyalty
                + brand_pack
                + express
                + other_ded_line
            )
        ).quantize(q)

        components = {
            "subtotal": subtotal,
            "net_order_value": net_order,
            "commissionable_value": commissionable,
            "service_fee": service_fee,
            "payment_mechanism_fee": payment_fee,
            "taxes_on_fees": taxes_on_fees,
            "tcs": tcs,
            "tds": tds,
            "gst_9_5": gst_95,
            "government_charges": gov_charges,
            "customer_compensation": customer_comp,
            "delivery_charges_recovery": delivery_recovery,
            "promo_recovery": promo,
            "ads_misc": ads,
            "loyalty": loyalty,
            "brand_pack": brand_pack,
            "express_fee": express,
            "packaging_charge": packaging,
            "delivery_fee": delivery_fee,
            "other_order_level_deductions": other_ded_line,
            "net_deductions": net_deductions,
            "net_additions": net_additions,
            "order_level_payout": reported_payout,
        }

        breakdown = FinancialBreakdown(
            platform=self.platform,
            order_id=order_id,
            formula_used=formula,
            gross_sale=(pos_sale or Decimal("0")).quantize(q),
            gross_order_value=net_order.quantize(q) if net_order else commissionable.quantize(q),
            commission=service_fee.quantize(q),
            payment_fee=payment_fee.quantize(q),
            delivery_fee=delivery_fee.quantize(q),
            packaging_adjustment=packaging.quantize(q),
            gst=(taxes_on_fees + gst_95).quantize(q),
            tcs=tcs.quantize(q),
            tds=tds.quantize(q),
            ads=ads.quantize(q),
            promo_recovery=promo.quantize(q),
            brand_pack=brand_pack.quantize(q),
            loyalty=loyalty.quantize(q),
            penalties=customer_comp.quantize(q),
            other_deductions=other_ded_line.quantize(q),
            other_additions=net_additions.quantize(q),
            total_deductions=total_deductions,
            calculated_payout=calculated,
            actual_payout=actual,
            deduction_summary=present_components(
                {
                    "commission_service_fee": service_fee,
                    "payment_fee": payment_fee,
                    "taxes_on_fees": taxes_on_fees,
                    "tcs": tcs,
                    "tds": tds,
                    "government_charges": gov_charges,
                    "promo_recovery": promo,
                    "ads": ads,
                    "loyalty": loyalty,
                    "brand_pack": brand_pack,
                    "customer_compensation": customer_comp,
                    "other_deductions": other_ded_line,
                    "net_deductions": net_deductions,
                }
            ),
            components=present_components(components),
            explanation=(
                f"Zomato {formula}: "
                f"GOV ₹{net_order.quantize(q)} − deductions ₹{total_deductions} "
                f"+ additions ₹{net_additions.quantize(q)} = ₹{calculated}; "
                f"actual payout ₹{actual}."
            ),
        )

        if not nov_col and not payout_col:
            breakdown.financial_status = FinancialStatus.INCOMPLETE_DATA
            breakdown.explanation = "Zomato settlement row missing Net Order Value / Order Level Payout columns."
            breakdown.financial_difference = (actual - calculated).quantize(q)
            return breakdown

        return self._finalize(breakdown, tolerance=tolerance)
