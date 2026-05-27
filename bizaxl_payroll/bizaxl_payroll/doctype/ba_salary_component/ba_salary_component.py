import frappe
from frappe.model.document import Document


class BASalaryComponent(Document):
    def validate(self):
        if not self.abbr:
            frappe.throw("Abbreviation is required.")

