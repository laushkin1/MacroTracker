# Macro Tracker Dashboard
This is a personal web application built with Django to track daily macronutrients (Calories, Protein, Fat, Carbs). It features a smart search system, color-coded limit tracking, and integration with the OpenFoodFacts API.

#### Temporary website - [MacroTracker](https://macrotracker.fly.dev)

## How to use?
1. Register and log in to the application.
2. Go to `⚙ Settings` -> `Edit Daily Limits` to set your daily nutritional goals. If limits are set to 0, the color gradients will be disabled.
3. On the main Dashboard, you can see your daily summary with a color-coded gradient:
   - Green indicates you are within your limits.
   - Red indicates you have exceeded your daily goals.
4. Click `+ Add Meal` to log food. You can search your local database by name or barcode.
5. If a product is missing, click `Manage Food Database` -> `+ Add New Food`. You can add food manually or click `Add via Barcode` to fetch nutritional data automatically from the OpenFoodFacts API.
6. Use the `Switch to Monthly View` button to see a calendar-style summary of your weekly and monthly progress.


## How to install? (Docker / Poetry)
This project is fully containerized using Docker and uses Poetry for dependency management.
1. Clone the repository:
   ```bash
   git clone https://github.com/laushkin1/MacroTracker.git
   cd MacroTracker
   ```
2. Create your environment variables file based on the example:
    ```bash
    cp .env.example .env
    ```

    (Open the .env file and fill in your desired database passwords and Django secret key).
3. Apply database migrations:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

4. Create an admin user to access the Django admin panel:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
    
5. The application is now running. Open your browser and go to `http://localhost:8000`


## Author
- [@laushkin1](https://github.com/laushkin1)