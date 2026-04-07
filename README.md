\# HRIS Project Setup



\## 1. Clone the repository

```bash

git clone https://github.com/haroldquijote/hris\_project1.git

cd hris_project1



#############

#step2
python -m venv venv

#step3
venv\\Scripts\\activate


#step4
pip install -r requirements.txt

#step5
python manage.py migrate

#step6
python manage.py createsuperuser

#step7
python manage.py runserver

#step 8
#http://127.0.0.1:8000/admin for admin panel then login your admin account

