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