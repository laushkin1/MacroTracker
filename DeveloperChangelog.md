### 2026-07-11
- Planning: Defined core project tasks and objectives.
- Planning: Finalized the technology stack.
- Setup: Configured Docker Compose for the local development environment.

### 2026-07-17
- Setup: Configured the database and data persistence mechanisms.
- Feature: Implemented core CRUD (Create, Read, Update, Delete) operations across the site.
- Docs: Documented and outlined the project specifications.

### 2026-07-18
- Feature: Implemented fallback logic for barcode scanning when a product is missing from the OpenFoodFacts database.
- Feature: Integrated the OpenFoodFacts API to support product searches by barcode.

### 2026-07-20
- Fix: Handled default macro and calorie limits of 0 correctly.
- UI/UX: Added a scrollable food list in the Add Meal menu.
- Refactor: Relocated the logout button to the settings menu.
- Chore: Initialized the Git repository for the project.
- UI/UX: Implemented a mobile-friendly responsive version of the application.
- UI/UX: Applied custom design and styling to the entire website.

### 2026-07-22
- Fix: Allowed floating-point values in the portion weight field when adding a meal.
- UI/UX: Moved the Home button to the top of the Dashboard.
- Fix: Displayed the product name in the deletion confirmation prompt for meals to match the behavior of product deletion.
- UI/UX: Added a 3-dots context menu to meal items containing Dublicate, Edit and Delete actions.

### 2026-07-23
- Refactor: Replaced the flat MealLog system with a hierarchical architecture featuring Meal (containers like Breakfast/Lunch) and MealItem (individual foods).
- Feature: Added full CRUD operations (Create, Read, Update, Delete) and duplication functionality for both Meal containers and MealItem entries.
- Feature: Implemented a dynamic "Add Meal" form that allows creating a meal container and adding multiple food items to it simultaneously.
- UI/UX: Redesigned the dashboard to display meals as expandable/collapsible containers with toggle arrows (▶/▼) optimized for mobile touch.
- UI/UX: Updated container styling to show total macro summaries, with individual MealItem cards visually indented underneath their respective containers.
- Chore: Generated and applied database migrations (0004_meal_mealitem.py) and updated all related URLs, views, and forms to support the new architecture.
- Feature: Implemented user-specific food databases by adding an owner (ForeignKey) relationship to the Food model.
- Security: Filtered all food-related queries (including the food list and JS search popups) to restrict users to only seeing and managing their own food items.
- Deployment: Integrated Fly.io for cloud hosting, connecting the production application to a persistent PostgreSQL database hosted on Neon.tech.
- Dependencies: Added gunicorn (WSGI HTTP server), whitenoise (static files management), and dj-database-url (database configuration via environment variables) for production readiness.
- Refactor: Updated settings.py to dynamically handle environment-based DEBUG, ALLOWED_HOSTS, and external DATABASE_URL parsing.

### 2026-07-26
- Feature: Automatically initialize 6 default meal containers (Breakfast, Morning Snack, Lunch, Afternoon Snack, Dinner, Second Dinner) for each day to eliminate empty-state friction for new users.
- Refactor: Reworked the + Add Food workflow into a unified modal/form experience allowing users to select any meal container on that date, search for food, and specify weight in a single step.
- Feature: Integrated OpenFoodFacts API search with an opt-in toggle directly into food selection views, enabling users to fetch and auto-save external products into their local database on the fly.
- UI/UX: Restructured the dashboard by moving the custom meal creation action to a dedicated + Add Meal button and introducing a standalone Calendar button for improved navigation clarity.
- UI/UX: Enhanced the food item edit view to support transferring items between different meal containers within the same date.

### 2026-07-28
- Feature: Replaced the "Search in OpenFoodFacts" checkbox with an advanced search mechanism, adding a dedicated arrow button that redirects users to a dedicated search results page displaying detailed food cards with macro breakdowns (calories, protein, fat, carbs) styled like the main Food Database.
- UI/UX: Streamlined the meal container architecture by removing custom meal creation entirely (deleted the "+ Add Meal" button, meal dropdown menus, and associated confirmation/form templates), locking the daily structure permanently to the 6 default meal slots.
- Bugfix: Fixed form validation handling when adding food items to meals, preventing accidental redirection and data loss if the weight field is left empty or invalid.
- Feature: Enhanced the OpenFoodFacts integration to display full macro nutrients (calories, protein, fat, and carbs per 100g) directly within search results and selection views.
- Feature: Added multi-unit measurement support for food items, allowing users to log consumption using custom units alongside standard grams and milliliters

### 2026-07-29
- Refactor: Eliminated the Meal model entirely from the database architecture to prevent database bloat and redundant record generation for daily meal slots.
- Architecture: Shifted the 6 standard meal categories (Breakfast, Morning Snack, Lunch, Afternoon Snack, Dinner, Second Dinner) to a purely frontend-rendered UI structure.
- Backend: Updated the data schema and API endpoints so that MealItem entries now bind directly to the date and user context, bypassing intermediate meal container tables.
- Database: Generated and applied database migrations to drop the Meal model and clean up obsolete foreign key dependencies.

### 2026-07-30
- UI/UX: Styled input default "0" values as gray placeholder text and allowed saving items without manually clearing zeroes.
- Bugfix: Fixed profile setup cancellation routing so users are correctly redirected to the dashboard instead of settings, and ensured user limits only save upon explicit form submission.
- Feature: Added pagination to the food database to limit the number of items displayed per page and improve load performance.

### 2026-07-31
- Refactor: Extracted helper functions (_parse_float_value and _resolve_food_from_post) to remove code duplication across meal item views, replaced print() calls with proper logging, tightened exception handling, optimized FoodListView sorting, and rewrote all comments in Simplified Technical English.
- Template & Routing: Renamed core templates (username_form.html to registration/change_username.html, monthly.html to calendar.html, and profile_form.html to tracker/edit_daily_limits_form.html).
- UI/UX: Updated weight and amount inputs to use type="text" and inputmode="decimal" for optimized mobile phone keyboards with automatic comma-to-dot replacement, and streamlined form validation rules for default and required values.

### 2026-08-02
- Backend: Switched numeric form fields to use Decimal instead of float for precise decimal storage without floating-point inaccuracies.
- Validation: Added case-insensitive duplicate food name validation in FoodForm to prevent users from creating items with existing names, complete with inline error messages and dedicated unit tests.
- UI/UX: Integrated error rendering into food_form.html to display clear red warning messages beneath specific fields upon invalid input.