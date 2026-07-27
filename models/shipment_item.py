from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ShipmentItem(models.Model):
    _name = "shipment.item"
    _description = "Shipment Item"

    shipment_id = fields.Many2one(
        "shipment.request",
        required=True,
        ondelete="cascade",
        index=True,
    )
    description = fields.Char(required=True)
    quantity = fields.Float(required=True, default=1.0)
    weight = fields.Float(string="Unit Weight (kg)", digits=(12, 2))
    volume = fields.Float(string="Unit Volume (m³)", digits=(12, 3))
    total_weight = fields.Float(
        compute="_compute_line_totals",
        store=True,
        digits=(12, 2),
    )
    total_volume = fields.Float(
        compute="_compute_line_totals",
        store=True,
        digits=(12, 3),
    )

    @api.depends("quantity", "weight", "volume")
    def _compute_line_totals(self):
        for item in self:
            item.total_weight = item.quantity * item.weight
            item.total_volume = item.quantity * item.volume

    @api.constrains("quantity", "weight", "volume")
    def _check_positive_values(self):
        # The brief gives every cargo item a quantity, a weight and a volume;
        # physically, anything that weighs something also occupies space, so
        # all three must be positive — no ghost cargo.
        for item in self:
            if item.quantity <= 0:
                raise ValidationError(
                    _("Item quantity must be greater than zero.")
                )
            if item.weight <= 0:
                raise ValidationError(
                    _(
                        "Item weight must be greater than zero — "
                        "every shipped item weighs something."
                    )
                )
            if item.volume <= 0:
                raise ValidationError(
                    _(
                        "Item volume must be greater than zero — "
                        "anything with weight occupies space."
                    )
                )

    def _check_shipment_editable(self):
        for item in self:
            if item.shipment_id.state not in ("draft", "preparing"):
                raise UserError(
                    _(
                        "The cargo of shipment %s can no longer be modified "
                        "once it has left preparation.",
                        item.shipment_id.name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        items = super().create(vals_list)
        items._check_shipment_editable()
        return items

    def write(self, vals):
        self._check_shipment_editable()
        res = super().write(vals)
        if "shipment_id" in vals:
            self._check_shipment_editable()
        return res

    def unlink(self):
        self._check_shipment_editable()
        return super().unlink()
