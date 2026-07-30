from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ShipmentType(models.Model):
    _name = "shipment.type"
    _description = "Shipment Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    category = fields.Selection(
        selection=[
            ("standard", "Standard"),
            ("express", "Express"),
            ("fragile", "Fragile"),
            ("international", "International"),
        ],
        required=True,
        default="standard",
    )
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "The shipment type code must be unique.",
    )
    _name_unique = models.Constraint(
        "UNIQUE(name)",
        "The shipment type name must be unique.",
    )

    @api.onchange("name")
    def _onchange_name_propose_code(self):
        # Propose a code from the name so the lead doesn't have to invent
        # one (e.g. "Express Freight" -> "EXPR"); it stays fully editable.
        for shipment_type in self:
            if shipment_type.name and not shipment_type.code:
                first_word = shipment_type.name.strip().split(" ")[0]
                shipment_type.code = first_word[:4].upper()

    @staticmethod
    def _normalize(vals):
        # Trim stray spaces and upper-case the code so " exp " and "EXP"
        # collide as intended instead of slipping past the unique check.
        if vals.get("code"):
            vals["code"] = vals["code"].strip().upper()
        if vals.get("name"):
            vals["name"] = vals["name"].strip()

    @api.constrains("name", "code")
    def _check_not_blank(self):
        for shipment_type in self:
            if not (shipment_type.name or "").strip():
                raise ValidationError(_("The shipment type name cannot be blank."))
            if not (shipment_type.code or "").strip():
                raise ValidationError(_("The shipment type code cannot be blank."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalize(vals)
        return super().write(vals)
