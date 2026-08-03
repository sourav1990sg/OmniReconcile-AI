"""Swiggy settlement financial engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from backend.platform_engines.base_engine import PlatformFinancialEngine
from backend.platform_engines.column_utils import find_column, money, pick_money, present_components
from backend.platform_engines.models import FinancialBreakdown, FinancialStatus


class SwiggyFinancialEngine(PlatformFinancialEngine):
    """
    Explain Swiggy Net Payable from annexure components.

    Primary formula:
        calculated = Net Payable (before TCS) − TCS − TDS
                   = Customer Payable − Total Swiggy Fee − Order Adjustments − TCS − TDS
    """

    @property
    def platform(self) -> str:
        return "swiggy"

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

        items_total = pick_money(settlement_row, cols, ("item's total", "items total"))
        packing = pick_money(settlement_row, cols, ("packing & service charges", "packing"))
        merchant_discount = pick_money(settlement_row, cols, ("merchant discount",))
        net_bill = pick_money(settlement_row, cols, ("net bill value (without taxes)", "net bill value"))
        gst_liability = pick_money(settlement_row, cols, ("gst liability of  merchant", "gst liability"))
        customer_payable = pick_money(
            settlement_row,
            cols,
            ("customer payable (net bill value after taxes", "customer payable"),
        )
        platform_fee = pick_money(
            settlement_row,
            cols,
            ("swiggy platform service fee g", "swiggy platform service fee"),
        )
        # Prefer column ending with " G" / exact fee amount
        for c in cols:
            cl = c.lower()
            if cl.startswith("swiggy platform service fee") and "%" not in cl and "chargeable" not in cl and "discount" not in cl:
                platform_fee = money(settlement_row.get(c))
                break

        fee_discount = pick_money(settlement_row, cols, ("discount on swiggy platform service fee",))
        collection = pick_money(settlement_row, cols, ("collection charges",))
        access = pick_money(settlement_row, cols, ("access charges",))
        cancel_charges = pick_money(settlement_row, cols, ("merchant cancellation charges",))
        call_center = pick_money(settlement_row, cols, ("call center service fees",))
        total_service_fee = pick_money(
            settlement_row,
            cols,
            ("total swiggy service fee (without taxes)", "total swiggy service fee"),
        )
        taxes_on_fee = pick_money(settlement_row, cols, ("taxes on swiggy fee",))
        total_fee_incl = pick_money(
            settlement_row,
            cols,
            ("total swiggy fee (including taxes)",),
        )
        delivery_sponsored = pick_money(
            settlement_row,
            cols,
            ("delivery fee (sponsored by merchant)",),
        )
        adjustments = pick_money(
            settlement_row,
            cols,
            ("total of order level adjustments",),
        )
        before_tcs = pick_money(
            settlement_row,
            cols,
            ("net payable amount (before tcs",),
        )
        tcs = pick_money(settlement_row, cols, ("tcs x1", "tcs"))
        tds = pick_money(settlement_row, cols, ("tds x2", "tds"))
        # Prefer exact TCS/TDS columns
        tcs_col = find_column(cols, ("tcs x1",))
        tds_col = find_column(cols, ("tds x2",))
        if tcs_col:
            tcs = money(settlement_row.get(tcs_col))
        if tds_col:
            tds = money(settlement_row.get(tds_col))

        net_payable_col = find_column(
            cols,
            (
                "net payable amount (after tcs and tds deduction)",
                "net payable amount (after tcs",
            ),
        )
        reported = money(settlement_row.get(net_payable_col)) if net_payable_col else Decimal("0")
        actual = (actual_payout if actual_payout is not None else reported).quantize(q)

        if before_tcs:
            formula = "Net Payable (before TCS) − TCS − TDS"
            calculated = (before_tcs - tcs - tds).quantize(q)
            gov = customer_payable if customer_payable else net_bill
        elif customer_payable and total_fee_incl:
            formula = "Customer Payable − Total Swiggy Fee − Adjustments − TCS − TDS"
            calculated = (customer_payable - total_fee_incl - adjustments - tcs - tds).quantize(q)
            gov = customer_payable
        else:
            formula = "Items − discounts − fees − taxes − TCS − TDS"
            gov = net_bill if net_bill else items_total
            fee_block = total_fee_incl if total_fee_incl else (platform_fee + taxes_on_fee)
            calculated = (gov - fee_block - adjustments - tcs - tds).quantize(q)

        total_deductions = (
            (total_fee_incl if total_fee_incl else (platform_fee + taxes_on_fee))
            + adjustments
            + tcs
            + tds
        ).quantize(q)

        components = {
            "items_total": items_total,
            "packing_service_charges": packing,
            "merchant_discount": merchant_discount,
            "net_bill_value": net_bill,
            "gst_liability": gst_liability,
            "customer_payable": customer_payable,
            "platform_service_fee": platform_fee,
            "discount_on_platform_fee": fee_discount,
            "collection_charges": collection,
            "access_charges": access,
            "cancellation_charges": cancel_charges,
            "call_center_fees": call_center,
            "total_service_fee_ex_tax": total_service_fee,
            "taxes_on_swiggy_fee": taxes_on_fee,
            "delivery_fee_sponsored": delivery_sponsored,
            "total_swiggy_fee_incl_tax": total_fee_incl,
            "order_level_adjustments": adjustments,
            "net_payable_before_tcs": before_tcs,
            "tcs": tcs,
            "tds": tds,
            "net_payable_after_tcs_tds": reported,
        }

        breakdown = FinancialBreakdown(
            platform=self.platform,
            order_id=order_id,
            formula_used=formula,
            gross_sale=(pos_sale or Decimal("0")).quantize(q),
            gross_order_value=(customer_payable or net_bill or items_total).quantize(q),
            commission=platform_fee.quantize(q),
            payment_fee=collection.quantize(q),
            delivery_fee=delivery_sponsored.quantize(q),
            packaging_adjustment=packing.quantize(q),
            gst=(gst_liability + taxes_on_fee).quantize(q),
            tcs=tcs.quantize(q),
            tds=tds.quantize(q),
            ads=Decimal("0.00"),
            promo_recovery=merchant_discount.quantize(q),
            brand_pack=Decimal("0.00"),
            loyalty=Decimal("0.00"),
            penalties=(cancel_charges + access).quantize(q),
            other_deductions=adjustments.quantize(q),
            other_additions=Decimal("0.00"),
            total_deductions=total_deductions,
            calculated_payout=calculated,
            actual_payout=actual,
            deduction_summary=present_components(
                {
                    "platform_service_fee": platform_fee,
                    "taxes_on_fee": taxes_on_fee,
                    "collection_charges": collection,
                    "cancellation_charges": cancel_charges,
                    "order_adjustments": adjustments,
                    "tcs": tcs,
                    "tds": tds,
                    "total_swiggy_fee": total_fee_incl,
                }
            ),
            components=present_components(components),
            explanation=(
                f"Swiggy {formula}: calculated ₹{calculated} vs actual net payable ₹{actual}."
            ),
        )

        if not net_payable_col and not before_tcs:
            breakdown.financial_status = FinancialStatus.INCOMPLETE_DATA
            breakdown.financial_difference = (actual - calculated).quantize(q)
            breakdown.explanation = "Swiggy settlement row missing Net Payable columns."
            return breakdown

        return self._finalize(breakdown, tolerance=tolerance)
