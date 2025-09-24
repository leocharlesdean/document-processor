# PostgreSQL Setup for Document Processor

## Required Version
- **PostgreSQL 12 or higher**

## Installation by OS

### Windows
- Download from https://www.postgresql.org/download/windows/
- Remember the password you set for `postgres` user during installation

### macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

## Setup for This Project

### 1. Create Database
```bash
psql -U postgres
```

```sql
CREATE DATABASE doc_intelligence;
CREATE USER doc_processor_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE doc_intelligence TO doc_processor_user;
\q
```

### 2. Create .env File
Create `.env` in your project root:

```bash
DATABASE_URL=postgresql://doc_processor_user:your_password@localhost:5432/doc_intelligence
```

### 3. Run Application
```bash
python main.py
```

The app will automatically create all required tables and indexes.
