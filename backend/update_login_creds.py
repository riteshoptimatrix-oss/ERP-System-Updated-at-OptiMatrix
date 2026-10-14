from pymongo import MongoClient
from app.core.security import hash_password
from datetime import datetime, timezone

client = MongoClient('mongodb://127.0.0.1:27017')
db = client['rgtech_erp']
users_col = db['users']

creds = [
    (1, 'amitpatel@rgtech.com', 'Amit Patel', 'Production', 'Production Supervisor', 'EMPLOYEE', 'Amit@rgtech.com'),
    (2, 'ananyaiyer@rgtech.com', 'Ananya Iyer', 'Billing & Finance', 'Billing Manager', 'ADMIN', 'Ananya123@rgtech.com'),
    (3, 'chetanprajapati@rgtech.com', 'Chetan Prajapati', 'Maintenance & Technical', 'Maintenance Technician', 'EMPLOYEE', 'Chetan@rgtech.com'),
    (4, 'deepakjoshi@rgtech.com', 'Deepak Joshi', 'HR & Admin', 'HR Executive', 'HR', 'Deepak@rgtech.com'),
    (5, 'hr@rgtech.com', 'Pooja Patel', 'HR', 'HR Manager', 'HR', 'admin123'),
    (6, 'manishtiwari@rgtech.com', 'Manish Tiwari', 'Billing & Finance', 'Accountant', 'EMPLOYEE', 'Manish@rgtech.com'),
    (7, 'mayan@rgtech.com', 'Mayank Gajjar', 'Employee General', 'Operations Executive', 'EMPLOYEE', 'admin123'),
    (8, 'nehamodi@rgtech.com', 'Neha Modi', 'Quality Control', 'QC Manager', 'QC_INSPECTOR', 'Neha@rgtech.com'),
    (9, 'priyashah@rgtech.com', 'Priya Shah', 'Sales & CRM', 'Sales Manager', 'SALES_DISPATCH', 'Priya@rgtech.com'),
    (10, 'rahulsharma@rgtech.com', 'Rahul Sharma', 'Production', 'Production Manager', 'PRODUCTION_MANAGER', 'Rahul@rgtech.com'),
    (11, 'rajeshkhatri@rgtech.com', 'Rajesh Khatri', 'Employee General', 'Operations Executive', 'EMPLOYEE', 'Rajesh123@rgtech.com'),
    (12, 'rameshsolanki@rgtech.com', 'Ramesh Solanki', 'Maintenance & Technical', 'Maintenance Manager', 'PRODUCTION_MANAGER', 'Ramesh@rgtech.com'),
    (13, 'rohangupta@rgtech.com', 'Rohan Gupta', 'Sales & CRM', 'Sales Executive', 'SALES_DISPATCH', 'Rohan@rgtech.com'),
    (14, 'sanjayrawat@rgtech.com', 'Sanjay Rawat', 'Dispatch & Logistic', 'Dispatch Manager', 'SALES_DISPATCH', 'Sanjay123@rgtech.com'),
    (15, 'sureshraina@rgtech.com', 'Suresh Raina', 'Inventory & Production', 'Inventory Manager', 'INVENTORY_MANAGER', 'Suresh@rgtech.com')
]

for sno, email, name, dept, role_title, role_enum, pwd in creds:
    pwd_hash = hash_password(pwd)
    existing = users_col.find_one({'email': email})
    if existing:
        users_col.update_one(
            {'_id': existing['_id']},
            {'$set': {
                'hashed_password': pwd_hash,
                'is_active': True,
                'must_change_password': False,
                'department': dept,
                'job_role': role_title,
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        print(f"Updated user {email}")
    else:
        users_col.insert_one({
            'email': email,
            'username': email.split('@')[0],
            'full_name': name,
            'hashed_password': pwd_hash,
            'role': role_enum,
            'department': dept,
            'job_role': role_title,
            'allowed_units': ['BOTH'],
            'is_active': True,
            'must_change_password': False,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        })
        print(f"Created user {email}")

print("ALL 15 CREDENTIALS CONFIGURED SUCCESSFULLY!")
