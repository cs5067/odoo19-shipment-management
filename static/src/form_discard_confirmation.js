import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Discarding a shipment form throws typed work away silently. Since drafts
 * can be saved half-finished on this model, offer the choice explicitly:
 * keep editing, or really discard.
 */
patch(FormController.prototype, {
    async discard() {
        if (this.model.root.resModel === "shipment.request") {
            const dirty = await this.model.root.isDirty();
            if (dirty) {
                return new Promise((resolve) => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Discard this information?"),
                        body: _t(
                            "The details you typed will be lost. If you want " +
                            "to finish later, use Save instead — the request " +
                            "stays as a draft."
                        ),
                        confirmLabel: _t("Discard"),
                        cancelLabel: _t("Keep editing"),
                        confirm: async () => {
                            await super.discard();
                            resolve();
                        },
                        cancel: () => resolve(),
                    });
                });
            }
        }
        return super.discard();
    },
});
