import frappe
from frappe.model.document import Document
from frappe.utils import flt, date_diff, getdate


class BASalarySlip(Document):
    def validate(self):
        self.set_salary_structure()
        self.pull_salary_components()
        self.calculate_totals()
        self.set_status()

    def set_salary_structure(self):
        if self.salary_structure:
            return
        assignment = frappe.db.sql("""
            SELECT salary_structure, base
            FROM `tabBA Salary Structure Assignment`
            WHERE employee = %s
            AND from_date <= %s
            ORDER BY from_date DESC
            LIMIT 1
        """, (self.employee, self.start_date), as_dict=True)

        if not assignment:
            frappe.throw(
                f"No salary structure assigned to {self.employee} "
                f"on or before {self.start_date}."
            )
        self.salary_structure = assignment[0].salary_structure
        self.base_salary = assignment[0].base

    def pull_salary_components(self):
        if self.earnings or self.deductions:
            return

        structure = frappe.get_doc("BA Salary Structure", self.salary_structure)
        base = flt(self.base_salary)

        self.earnings = []
        for row in structure.earnings:
            amount = self._calculate_component_amount(row, base)
            self.append("earnings", {
                "salary_component": row.salary_component,
                "abbr": row.abbr,
                "amount": amount,
            })

        self.deductions = []
        for row in structure.deductions:
            amount = self._calculate_component_amount(row, base)
            self.append("deductions", {
                "salary_component": row.salary_component,
                "abbr": row.abbr,
                "amount": amount,
            })

    def _calculate_component_amount(self, row, base):
        if row.amount_based_on_formula and row.formula:
            try:
                amount = flt(eval(row.formula, {"base": base, "flt": flt}))
            except Exception as e:
                frappe.throw(
                    f"Error in formula for {row.salary_component}: {e}"
                )
        else:
            amount = flt(row.amount)
        return amount

    def calculate_totals(self):
        self.gross_pay = sum(flt(e.amount) for e in (self.earnings or []))
        self.total_deductions = sum(flt(d.amount) for d in (self.deductions or []))
        self.net_pay = self.gross_pay - self.total_deductions

        if self.working_days and self.payment_days:
            ratio = flt(self.payment_days) / flt(self.working_days)
            self.gross_pay = flt(self.gross_pay * ratio, 2)
            self.net_pay = flt(self.net_pay * ratio, 2)

    def set_status(self):
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"

    def on_submit(self):
        self.set_status()
        self.set_accounts()
        self.make_gl_entries()

    def on_cancel(self):
        self.status = "Cancelled"
        self.cancel_gl_entries()

    def set_accounts(self):
        if self.salary_payable_account and self.salary_expense_account:
            return
        structure = frappe.get_doc("BA Salary Structure", self.salary_structure)
        if not self.salary_payable_account:
            self.salary_payable_account = structure.salary_payable_account
        if not self.salary_expense_account:
            self.salary_expense_account = structure.salary_expense_account

        if not self.salary_payable_account or not self.salary_expense_account:
            frappe.throw(
                "Please set Salary Payable and Salary Expense accounts "
                "on the Salary Structure before submitting."
            )

    def make_gl_entries(self):
        from bizaxl_erp.bizaxl_accounts.gl_handler import make_gl_entry

        make_gl_entry(
            company=self.company,
            posting_date=self.posting_date,
            account=self.salary_expense_account,
            debit=self.gross_pay,
            credit=0,
            voucher_type="BA Salary Slip",
            voucher_no=self.name,
            remarks=f"Salary for {self.employee_name} - {self.start_date} to {self.end_date}",
        )
        make_gl_entry(
            company=self.company,
            posting_date=self.posting_date,
            account=self.salary_payable_account,
            debit=0,
            credit=self.net_pay,
            voucher_type="BA Salary Slip",
            voucher_no=self.name,
            remarks=f"Net pay for {self.employee_name}",
        )
        for ded in (self.deductions or []):
            component = frappe.get_doc("BA Salary Component", ded.salary_component)
            if component.account and flt(ded.amount) > 0:
                make_gl_entry(
                    company=self.company,
                    posting_date=self.posting_date,
                    account=component.account,
                    debit=0,
                    credit=flt(ded.amount),
                    voucher_type="BA Salary Slip",
                    voucher_no=self.name,
                    remarks=f"Deduction: {ded.salary_component}",
                )

    def cancel_gl_entries(self):
        frappe.db.sql("""
            UPDATE `tabBA GL Entry`
            SET is_cancelled = 1
            WHERE voucher_type = 'BA Salary Slip'
            AND voucher_no = %s
        """, self.name)

