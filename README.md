# Grace Community Church Website

This is a full-stack church website with a Flask backend and a vanilla JavaScript frontend.

## Project Structure

```
church-website/
├── frontend/
│   ├── index.html
│   ├── about.html
│   ├── services.html
│   ├── events.html
│   ├── contact.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js
│   └── images/
│       └── (placeholder folders)
├── backend/
│   ├── app.py
│   ├── models.py
│   ├── routes.py
│   ├── config.py
│   ├── requirements.txt
│   └── database.db
└── README.md
```

## Setup and Usage

### Backend

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    -   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    -   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```

4.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the Flask application:**
    ```bash
    flask run
    ```

    The backend will be running at `http://127.0.0.1:5000`.

### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Open the `index.html` file in your browser.** You can do this by double-clicking the file or by using a live server extension in your code editor.

## API Endpoints

- `GET /api/events`: Fetch all upcoming events.
- `POST /api/events`: Create a new event (admin only).
- `GET /api/events/{id}`: Fetch a specific event.
- `PUT /api/events/{id}`: Update an event (admin only).
- `DELETE /api/events/{id}`: Delete an event (admin only).
- `GET /api/services`: Fetch service times.
- `POST /api/services`: Update service times (admin only).
- `POST /api/contact`: Submit a contact form.
- `POST /api/prayer-requests`: Submit a prayer request.
- `GET /api/announcements`: Fetch announcements.
- `POST /api/announcements`: Create an announcement (admin only).
- `POST /api/newsletter`: Subscribe to the newsletter.

### Admin Authentication

- `POST /api/admin/login`: Login as an admin.
- `POST /api/admin/logout`: Logout.

**Default Admin Credentials:**
- **Username:** admin
- **Password:** admin123
