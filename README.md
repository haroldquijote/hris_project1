HRIS – Human Resource Information System
A comprehensive HRIS built with Django Rest Framework, covering employee management, attendance, leave, overtime, payroll, holidays, recruitment, AI‑powered resume screening, role‑based access control, and audit logging.

Tech Stack
Backend: Django, Django Rest Framework

Database: PostgreSQL 

Authentication: JWT (SimpleJWT)

AI/ML: DeepSeek API for resume grading, Microsoft Presidio for anonymization, spaCy

Documentation: Swagger/OpenAPI (drf‑spectacular)

Features
Employee CRUD with photo upload

Attendance tracking with late/undertime/absence logic

Work schedules and rest day premiums

Leave management with pro‑rated annual credits and balances

Overtime requests with approval workflow

Payroll computation (gross, deductions, net, 13th month)

Government contributions (SSS, PhilHealth, Pag‑IBIG, Tax)

Holiday management with pay multipliers

AI‑powered recruitment: job postings, resume upload, anonymized grading

Role‑based access control (HRAdmin & HRAssistant with delegatable privileges)

Audit trail for all critical actions

Dashboard aggregation with summary endpoints

Swagger UI for API exploration

Setup Instructions
1. Clone the repository
bash
git clone https://github.com/haroldquijote/hris_project1
cd hris_project1
2. Create and activate a virtual environment
bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
3. Install dependencies
bash
pip install -r requirements.txt
4. Download spaCy model (for recruitment anonymization)
bash
python -m spacy download en_core_web_lg
5. Set up environment variables
Create a .env file in the project root:

text
DEEPSEEK_API_KEY=sk-your-key-here
6. Run migrations
bash
python manage.py migrate
7. Seed government tables
bash
python manage.py seed_govt_tables
8. Create the first HR Admin
bash
python manage.py create_hr_admin --username admin --password Changeme123 --company_id EMP001
Replace EMP001 with an existing employee's company ID (optional).

9. Start the development server
bash
python manage.py runserver
Access Swagger docs at http://127.0.0.1:8000/api/docs/.

Default Admin Credentials
Username: admin

Password: Changeme123

(Change this password after first login.)

Main Modules
App	Description
users	  - Authentication, user profile, RBAC, assistant management
employees -	Employee, department, job title, work schedule, salary, allowances
attendance-	Attendance records, work schedules
leave	  - Leave types, requests, grants, balances, adjustments
overtime  - Overtime requests, configuration
payroll	  - Pay periods, payslips, government contributions, reports
holidays  -	Philippine holiday list & checks
recruitment - Job postings, candidates, AI resume screening
dashboard - Consolidated summary endpoint
audit     - Audit log for all state‑changing actions

Test Users
HR Admin
username: admin

password: Changeme123

HR Assistant (example)
created via /api/auth/assistants/

default password: Changeme123

must change password on first login

Documentation
Frontend Developer Guide: See docs/frontend_guide.docx or the root FRONTEND.md

Swagger UI: /api/docs/

Environment Variables
Variable	Required	Description
DEEPSEEK_API_KEY	Yes	API key for AI‑powered resume grading
SECRET_KEY	Yes	Django secret key
DEBUG	No	Set to False in production

Security Notes
Never commit .env or real API keys.

The system uses JWT for authentication and role‑based permissions.

Resume anonymization strips PII before sending to external AI APIs.

