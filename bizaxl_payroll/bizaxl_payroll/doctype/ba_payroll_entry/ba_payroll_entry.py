import frappe
from frappe.model.document import Document
from frappe.utils import flt


class BAPayrollEntry(Document):
    def validate(self):
        if self.start_date >= self.end_date:
            frappe.throw("End Date must be after Start Date.")
        self.set_status()

    def set_status(self):
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"

    @frappe.whitelist()
    def create_salary_slips(self):
        """Create salary slips for all eligible employees."""
        if self.docstatus != 0:
            frappe.throw("Can only create salary slips from a Draft Payroll Entry.")

        employees = self.get_eligible_employees()
        if not employees:
            frappe.throw("No eligible employees found for the given filters.")

        created = 0
        skipped = 0

        for emp in employees:
            existing = frappe.db.exists("BA Salary Slip", {
                "employee": emp.name,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "docstatus": ("!=", 2),
            })
            if existing:
                skipped += 1
                continue

            slip = frappe.get_doc({
                "doctype": "BA Salary Slip",
                "employee": emp.name,
                "company": self.company,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "posting_date": self.posting_date,
                "payroll_entry": self.name,
                "salary_payable_account": self.salary_payable_account,
                "salary_expense_account": self.salary_expense_account,
            })
            slip.flags.ignore_permissions = True
            slip.insert()
            created += 1

        self.update_summary()
        frappe.db.commit()

        return {
            "created": created,
            "skipped": skipped,
            "message": f"{created} salary slips created, {skipped} already existed.",
        }

    @frappe.whitelist()
    def submit_salary_slips(self):
        """Submit all draft salary slips linked to this payroll entry."""
        slips = frappe.get_all("BA Salary Slip", filters={
            "payroll_entry": self.name,
            "docstatus": 0,
        }, fields=["name"])

        submitted = 0
        errors = []

        for slip in slips:
            try:
                doc = frappe.get_doc("BA Salary Slip", slip.name)
                doc.submit()
                submitted += 1
            except Exception as e:
                errors.append(f"{slip.name}: {str(e)}")

        self.update_summary()
        frappe.db.commit()

        result = {"submitted": submitted}
        if errors:
            result["errors"] = errors
        return result

    def get_eligible_employees(self):
        filters = {
            "status": "Active",
            "company": self.company,
        }
        if self.department:
            filters["department"] = self.department
        if self.designation:
            filters["designation"] = self.designation

        employees = frappe.get_all("BA Employee",
            filters=filters,
            fields=["name", "employee_name", "department", "designation"]
        )

        eligible = []
        for emp in employees:
            has_structure = frappe.db.exists("BA Salary Structure Assignment", {
                "employee": emp.name,
                "from_date": ("<=", self.start_date),
            })
            if has_structure:
                eligible.append(emp)

        return eligible

    def update_summary(self):
        slips = frappe.get_all("BA Salary Slip", filters={
            "payroll_entry": self.name,
            "docstatus": ("!=", 2),
        }, fields=["gross_pay", "net_pay", "total_deductions"])

        self.total_employees = len(slips)
        self.total_gross_pay = sum(flt(s.gross_pay) for s in slips)
        self.total_net_pay = sum(flt(s.net_pay) for s in slips)
        self.total_deductions = sum(flt(s.total_deductions) for s in slips)
        self.status = "Created" if self.total_employees > 0 else "Draft"
        self.db_update()

    def on_submit(self):
        self.set_status()
        unsubmitted = frappe.get_all("BA Salary Slip", filters={
            "payroll_entry": self.name,
            "docstatus": 0,
        }, fields=["name"])

        if unsubmitted:
            frappe.throw(
                f"{len(unsubmitted)} salary slips are still in Draft. "
                f"Please submit all salary slips before submitting the Payroll Entry."
            )

    def on_cancel(self):
        self.status = "Cancelled"
        submitted_slips = frappe.get_all("BA Salary Slip", filters={
            "payroll_entry": self.name,
            "docstatus": 1,
        }, fields=["name"])

        for slip in submitted_slips:
            doc = frappe.get_doc("BA Salary Slip", slip.name)
            doc.cancel()

        frappe.db.commit()
