import frappe
from frappe.utils import flt
def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "BA Employee", "width": 140},
        {"fieldname": "employee_name", "label": "Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "salary_structure", "label": "Structure", "fieldtype": "Data", "width": 140},
        {"fieldname": "base_salary", "label": "Base", "fieldtype": "Currency", "width": 120},
        {"fieldname": "gross_pay", "label": "Gross", "fieldtype": "Currency", "width": 120},
        {"fieldname": "total_deductions", "label": "Deductions", "fieldtype": "Currency", "width": 120},
        {"fieldname": "net_pay", "label": "Net Pay", "fieldtype": "Currency", "width": 120},
        {"fieldname": "start_date", "label": "Period", "fieldtype": "Date", "width": 100},
    ]
    conditions = "WHERE docstatus = 1"
    values = {}
    if filters.get("company"):
        conditions += " AND company = %(company)s"
        values["company"] = filters["company"]
    if filters.get("from_date"):
        conditions += " AND start_date >= %(from_date)s"
        values["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND end_date <= %(to_date)s"
        values["to_date"] = filters["to_date"]
    data = frappe.db.sql(f"""
        SELECT employee, employee_name, salary_structure,
               base_salary, gross_pay, total_deductions, net_pay, start_date
        FROM `tabBA Salary Slip`
        {conditions}
        ORDER BY start_date DESC, employee_name
    """, values, as_dict=True)
    return columns, data
