import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("leather_inspection_data_entry", {
    steps: () => [
        {
            content: "The assigned queue is the leather inspection list",
            trigger: ".o_leather_inspection_list",
        },
        {
            content: "Open the search filters",
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            content: "Filter to My Assigned Inspections",
            trigger: ".o_filter_menu .o_menu_item:contains('My Assigned Inspections')",
            run: "click",
        },
        {
            content: "Open the assigned inspection",
            trigger: ".o_leather_inspection_list .o_data_row",
            run: "click",
        },
        {
            content: "Open the assigned inspection form",
            trigger: ".o_leather_inspection_form",
        },
        {
            content: "Context is shown as a label, without an inventory link",
            trigger: ".o_leather_inspection_form .o_field_widget[name=lot_label]",
        },
        {
            content: "Product context is read-only",
            trigger: ".o_leather_inspection_form .o_field_widget[name=product_id]",
        },
        {
            content: "Enter the measured area",
            trigger: ".o_leather_inspection_form .o_field_widget[name=measured_area] input",
            run: "edit 4.500",
        },
        {
            content: "Enter the usable area",
            trigger: ".o_leather_inspection_form .o_field_widget[name=usable_area] input",
            run: "edit 4.250",
        },
        {
            content: "Open the grade list",
            trigger: ".o_leather_inspection_form .o_field_widget[name=grade] .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "Choose Grade A",
            trigger: ".o_select_menu_menu .o_select_menu_item:contains('Grade A')",
            run: "click",
        },
        {
            content: "Submit is available only in the assigned state",
            trigger: ".o_leather_inspection_form button[name=action_submit]",
            run: "click",
        },
        {
            content: "The inspection is submitted",
            trigger: ".o_leather_inspection_form button.o_arrow_button_current[data-value='submitted']",
        },
    ],
});

registry.category("web_tour.tours").add("leather_inspection_operator_review", {
    steps: () => [
        {
            content: "Open the submitted inspection",
            trigger: ".o_leather_inspection_form",
        },
        {
            content: "The operator can open the lot",
            trigger: ".o_leather_inspection_form .o_field_widget[name=lot_id]",
        },
        {
            content: "The receipt link is available",
            trigger: ".o_leather_inspection_form .o_field_widget[name=picking_id]",
        },
        {
            content: "Approve is available on a submitted inspection",
            trigger: ".o_leather_inspection_form button[name=action_approve]",
            run: "click",
        },
        {
            content: "The inspection is approved",
            trigger: ".o_leather_inspection_form button.o_arrow_button_current[data-value='approved']",
        },
        {
            content: "The reviewer is shown",
            trigger: ".o_leather_inspection_form .o_field_widget[name=reviewer_id]",
        },
    ],
});
