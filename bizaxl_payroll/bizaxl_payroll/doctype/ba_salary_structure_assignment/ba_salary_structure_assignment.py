import frappe
from frappe.model.document import Document


class BASalaryStructureAssignment(Document):
    def validate(self):
        if not self.base or self.base <= 0:
            frappe.throw("Base salary must be greater than zero.")
        self.validate_duplicate()

    def validate_duplicate(self):
        existing = frappe.db.exists("BA Salary Structure Assignment", {
            "employee": self.employee,
            "from_date": self.from_date,
            "name": ("!=", self.name or ""),
        })
        if existing:
            frappe.throw(
                f"A salary structure assignment already exists for "
                f"{self.employee} from {self.from_date}."
            )
