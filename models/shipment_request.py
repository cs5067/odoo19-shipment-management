import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ShipmentRequest(models.Model):
    _name = "shipment.request"
    _description = "Shipment Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        default=lambda self: _("New"),
        copy=False,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    shipment_type_id = fields.Many2one(
        "shipment.type",
        string="Shipment Type",
        required=True,
        tracking=True,
    )
    origin = fields.Char(required=True, tracking=True)
    destination = fields.Char(required=True, tracking=True)
    pickup_date = fields.Date(
        required=True, tracking=True, default=fields.Date.context_today
    )
    delivery_date = fields.Date(required=True, tracking=True)
    item_ids = fields.One2many(
        "shipment.item",
        "shipment_id",
        string="Items",
        copy=True,
    )
    total_weight = fields.Float(
        compute="_compute_totals",
        store=True,
        digits=(12, 2),
    )
    total_volume = fields.Float(
        compute="_compute_totals",
        store=True,
        digits=(12, 3),
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("preparing", "Preparing"),
            ("with_courier", "With Courier"),
            ("on_the_way", "On The Way"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        group_expand=True,
    )
    delivered_on = fields.Datetime(
        string="Delivered On",
        readonly=True,
        copy=False,
        help="When the shipment was actually marked delivered.",
    )

    _name_unique = models.Constraint(
        "UNIQUE(name)",
        "The shipment reference must be unique.",
    )

    @api.depends("item_ids.total_weight", "item_ids.total_volume")
    def _compute_totals(self):
        for shipment in self:
            shipment.total_weight = sum(shipment.item_ids.mapped("total_weight"))
            shipment.total_volume = sum(shipment.item_ids.mapped("total_volume"))

    @api.constrains("pickup_date", "delivery_date")
    def _check_dates(self):
        for shipment in self:
            if shipment.delivery_date < shipment.pickup_date:
                raise ValidationError(
                    _("The delivery date cannot be before the pickup date.")
                )

    @api.constrains("pickup_date")
    def _check_pickup_not_past(self):
        today = fields.Date.context_today(self)
        for shipment in self:
            if shipment.pickup_date and shipment.pickup_date < today:
                raise ValidationError(
                    _(
                        "Pickup date cannot be in the past. "
                        "Choose today or a later date."
                    )
                )

    @api.constrains("origin", "destination")
    def _check_route(self):
        for shipment in self:
            same = (shipment.origin or "").strip().lower() == (
                shipment.destination or ""
            ).strip().lower()
            if same:
                raise ValidationError(
                    _("Origin and destination cannot be the same place.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = self.env["ir.sequence"].next_by_code(
                "shipment.request"
            )
            if vals.get("state") not in (None, False, "draft"):
                raise UserError(
                    _("A new shipment request always starts as a draft.")
                )
        return super().create(vals_list)

    def write(self, vals):
        # The lifecycle advances through the workflow buttons only — the
        # status field cannot be edited directly (assignment §5). Every
        # action method funnels its state change through _advance_state.
        if "state" in vals and not self.env.context.get(
            "shipment_state_change"
        ):
            raise UserError(
                _(
                    "The shipment status cannot be edited directly. "
                    "Use the workflow buttons to move it forward."
                )
            )
        return super().write(vals)

    def _advance_state(self, vals):
        return self.with_context(shipment_state_change=True).write(vals)

    def action_confirm(self):
        for shipment in self:
            if shipment.state != "draft":
                raise UserError(
                    _(
                        "Only draft requests can be confirmed. "
                        "%s is already in progress.",
                        shipment.name,
                    )
                )
            shipment._advance_state({"state": "preparing"})

    def action_hand_to_courier(self):
        for shipment in self:
            if shipment.state != "preparing":
                raise UserError(
                    _(
                        "Shipment %s can only be handed to the courier "
                        "while it is being prepared.",
                        shipment.name,
                    )
                )
            if not shipment.item_ids:
                raise UserError(
                    _(
                        "Shipment %s cannot leave without cargo. "
                        "Add at least one item before handing it to the courier.",
                        shipment.name,
                    )
                )
            shipment._advance_state({"state": "with_courier"})

    def action_on_the_way(self):
        for shipment in self:
            if shipment.state != "with_courier":
                raise UserError(
                    _(
                        "Shipment %s must be with the courier before "
                        "it can start transit.",
                        shipment.name,
                    )
                )
            shipment._advance_state({"state": "on_the_way"})

    def action_deliver(self):
        for shipment in self:
            if shipment.state != "on_the_way":
                raise UserError(
                    _(
                        "Shipment %s must be on the way before it can "
                        "be marked as delivered.",
                        shipment.name,
                    )
                )
            shipment._advance_state(
                {
                    "state": "delivered",
                    "delivered_on": fields.Datetime.now(),
                }
            )

    def action_cancel(self):
        for shipment in self:
            if shipment.state in ("delivered", "cancelled"):
                raise UserError(
                    _(
                        "%s can no longer be cancelled: it is already "
                        "delivered or cancelled.",
                        shipment.name,
                    )
                )
            shipment._advance_state({"state": "cancelled"})

    def action_reset_to_draft(self):
        for shipment in self:
            if shipment.state != "cancelled":
                raise UserError(
                    _(
                        "Only cancelled shipments can be reset to draft. "
                        "Cancel %s first.",
                        shipment.name,
                    )
                )
            shipment._advance_state({"state": "draft", "delivered_on": False})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_in_progress(self):
        for shipment in self:
            if shipment.state not in ("draft", "cancelled"):
                raise UserError(
                    _(
                        "%s cannot be deleted while it is in progress or "
                        "delivered. Cancel it instead to keep its history.",
                        shipment.name,
                    )
                )

    def _get_barcode_base64(self):
        self.ensure_one()
        barcode = self.env["ir.actions.report"].barcode(
            "Code128", self.name, width=600, height=120, humanreadable=1
        )
        return base64.b64encode(barcode).decode()
