import frappe
from frappe.model.document import Document


class BASalaryStructure(Document):
    def validate(self):
        self.validate_components()

    def validate_components(self):
        seen = set()
        for row in (self.earnings or []) + (self.deductions or []):
            if row.salary_component in seen:
                frappe.throw(f"Duplicate component: {row.salary_component}")
            seen.add(row.salary_component)

