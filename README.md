# Snickr

Snickr is a lightweight Slack-style collaboration platform built with Flask and PostgreSQL.

Users can create workspaces, manage channels, invite members, communicate through channel-based messaging and search messages.

---

# Features

## Authentication

* User registration and login
* Secure password hashing using Werkzeug
* Session-based authentication
* Logout support
* Flash message notifications

---

## Workspace System

* Create workspaces
* Join workspaces through invitations
* Workspace invitation history
* Workspace member management
* Role-based permissions:

  * creator
  * admin
  * member

### Workspace Permissions

| Role    | Permissions                 |
| ------- | --------------------------- |
| creator | Manage admins, invite users |
| admin   | Invite users                |
| member  | View and participate        |

---

## Channel System

Supports three channel types:

### Public Channel

* Any workspace member can access
* Automatically joins the channel on access

### Private Channel

* Only invited members can access
* Only channel creator can invite users

### Direct Channel

* Maximum of two users
* Used for direct communication

---

## Messaging System

* Channel-based messaging
* Message history display
* Timestamped messages
* User information attached to messages
* Search messages

---

## Invitation System

### Workspace Invitations

* Send invitations by email
* Accept / reject invitations
* Invitation history tracking

### Channel Invitations

* Private/direct channel invitations
* Accept / reject invitations
* Invitation history tracking

---

# Tech Stack

## Backend

* Flask
* PostgreSQL
* psycopg2

## Frontend

* HTML
* CSS
* JavaScript
* Jinja2 Templates

## Authentication

* Flask Session
* Werkzeug Security

---

# Setup

## 1. Clone Repository

```bash
git clone https://github.com/lin1318/snicker.git
cd Snickr
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate:

### Windows

```bash
venv\Scripts\activate
```

### Mac/Linux

```bash
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install flask psycopg2
```

---

## 4. Configure PostgreSQL

Create a PostgreSQL database.

Then update your database configuration in `db.py`.

Example:

```python
psycopg2.connect(
    host="localhost",
    database="snickr",
    user="postgres",
    password="your_password"
)
```

---

## 5. Initialize Database

Run the SQL schema:

```bash
psql -U postgres -d snickr -f schema.sql
```

---

## 6. Run Application

```bash
python app.py
```

Open:

```txt
http://127.0.0.1:5000
```