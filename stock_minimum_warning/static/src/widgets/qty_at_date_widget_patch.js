/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import {
    QtyAtDatePopover,
    QtyAtDateWidget,
    qtyAtDateWidget,
} from "@sale_stock/widgets/qty_at_date_widget";

// ---------------------------------------------------------------------------
// QtyAtDateWidget – extend calcData with draft-quotation information
// ---------------------------------------------------------------------------

patch(QtyAtDateWidget.prototype, {
    /**
     * Extend the original calcData initialisation to expose:
     *
     *   qty_in_draft_quotations  – total qty in other draft/sent orders
     *   net_forecasted_qty       – forecasted − draft-quotation demand
     *   draft_quotation_warning  – yellow flag (enough total stock but net
     *                              forecasted falls below qty_to_deliver)
     *   label_*                  – UI strings translated server-side (Python _())
     */
    initCalcData() {
        super.initCalcData(...arguments);
        const { data } = this.props.record;

        const draftQty      = data.qty_in_draft_quotations || 0;
        const forecastedQty = data.virtual_available_at_date || 0;
        const qtyToDeliver  = data.qty_to_deliver || 0;
        const netForecast   = forecastedQty - draftQty;

        this.calcData.qty_in_draft_quotations = draftQty;
        this.calcData.net_forecasted_qty      = netForecast;

        // Yellow: enough total stock for this line alone, but the net forecasted
        // quantity (after removing demand from other draft quotations) is insufficient.
        // Only meaningful for draft/sent non-MTO lines (red is already handled by
        // the base widget's calcData.forecasted_issue).
        this.calcData.draft_quotation_warning = (
            ["draft", "sent"].includes(data.state) &&
            !data.is_mto &&
            forecastedQty >= qtyToDeliver &&     // not already red
            netForecast   <  qtyToDeliver        // but net is insufficient
        );

        // UI labels translated by Python and sent as regular char fields so the
        // correct language is always used without depending on the JS bundle.
        this.calcData.label_in_unconfirmed  = data.draft_quotation_label_unconfirmed  || "In Unconfirmed Quotations";
        this.calcData.label_net_forecasted  = data.draft_quotation_label_net_forecasted || "Net Forecasted";
        this.calcData.label_view_drafts     = data.draft_quotation_label_view_drafts   || "View Draft Quotations";
    },
});

// ---------------------------------------------------------------------------
// QtyAtDatePopover – add ORM service + action to open draft quotations
// ---------------------------------------------------------------------------

patch(QtyAtDatePopover.prototype, {
    setup() {
        super.setup(...arguments);
        this.ormService = useService("orm");
    },

    /**
     * Call the server-side action that returns a window action listing all
     * draft/sent quotations that contain the same product as this line.
     */
    async openDraftQuotations() {
        const lineId = this.props.record.resId;
        const action = await this.ormService.call(
            "sale.order.line",
            "action_view_draft_quotations",
            [lineId],
        );
        this.props.close();
        await this.actionService.doAction(action);
    },
});

// ---------------------------------------------------------------------------
// Registry entry – declare new field dependencies on the widget registration
// (must be patched on the registry object, not on the component class)
// ---------------------------------------------------------------------------

const stockMinimumWarningWidget = {
    ...qtyAtDateWidget,
    fieldDependencies: [
        ...(qtyAtDateWidget.fieldDependencies || []),
        { name: "qty_in_draft_quotations",           type: "float" },
        { name: "draft_quotation_label_unconfirmed", type: "char"  },
        { name: "draft_quotation_label_net_forecasted", type: "char" },
        { name: "draft_quotation_label_view_drafts", type: "char"  },
    ],
};
patch(qtyAtDateWidget, stockMinimumWarningWidget);
