## Installation Settings

1. Clone this repository to your local machine:
```bash
git clone https://github.com/aniru-dh21/https://github.com/aniru-dh21/SSE-Project-Group-18.git
```
2. Install the required Python packages:
```bash
pip install -r requirements.txt
```
3. Set up your MySQL database accordingly to `settings.py`
4. First create migrations if not present
```
python manage.py makemigrations
```
5. Then migrate those migrations to database:
```
python manage.py migrate
```
6. Create a superuser in Django for generating packages
```
python manage.py createsuperuser
```
7. Run the application
```
python manage.py runserver
```
8. If you have added a new package, go to `http://127.0.0.1:8000/packages/generate/` and click on check boxes provided and those will automatically generate packages.
