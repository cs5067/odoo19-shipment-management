{
    "name": "Shipment Management",
    "summary": "Register shipment requests with lifecycle tracking and driver PDF orders",
    "version": "19.0.6.1.0",
    "category": "Inventory/Delivery",
    "author": "Logistics Team",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/shipment_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/shipment_type_views.xml",
        "views/shipment_request_views.xml",
        "views/shipment_menus.xml",
        "report/shipment_report.xml",
        "report/shipment_report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "shipment_management/static/src/**/*",
        ],
    },
    "application": True,
    "installable": True,
}
