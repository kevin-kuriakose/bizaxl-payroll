import frappe
from frappe.utils import flt
def execute(filters=None):
    filters = filters or {}
    columns = [
        {"fieldname": "employee", "label": "Employee", "fieldtype": "Link", "options": "BA Employee", "width": 140},
        {"fieldname": "employee_name", "label": "Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "department", "label": "Department", "fieldtype": "Data", "width": 140},
        {"fieldname": "start_date", "label": "From", "fieldtype": "Date", "width": 100},
        {"fieldname": "end_date", "label": "To", "fieldtype": "Date", "width": 100},
        {"fieldname": "gross_pay", "label": "Gross Pay", "fieldtype": "Currency", "width": 130},
        {"fieldname": "total_deductions", "label": "Deductions", "fieldtype": "Currency", "width": 130},
        {"fieldname": "net_pay", "label": "Net Pay", "fieldtype": "Currency", "width": 130},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
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
    if filters.get("employee"):
        conditions += " AND employee = %(employee)s"
        values["employee"] = filters["employee"]
    data = frappe.db.sql(f"""
        SELECT s.employee, s.employee_name, e.department,
               s.start_date, s.end_date,
               s.gross_pay, s.total_deductions, s.net_pay, s.status
        FROM `tabBA Salary Slip` s
        LEFT JOIN `tabBA Employee` e ON e.name = s.employee
        {conditions}
        ORDER BY s.start_date DESC, s.employee_name
    """, values, as_dict=True)
    return columns, data
