# Development image for the Project Management System (step 08).
# Not for production: it runs Django's development server as root.
#python:3.12.16-slim-trixie is already a ready-made Docker image.
# Exact Python patch and Debian release pinned (step 10, Q-74): a rebuild
# never changes underneath us. Updating it is a deliberate one-line change.
FROM python:3.12.16-slim-trixie

# No .pyc files on the bind mount; logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

 #Make /app the main working folder inside the container.
WORKDIR /app 

# Dependencies first, so this layer is cached until requirements.txt changes.
#Copy requirements.txt into /app.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the application code.Copy the project code into /app.
COPY . .

#Declare that the app uses port 8000.
EXPOSE 8000

#When the container starts, run the Django development server on port 8000.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
