### SayIt Backend 🎙️
SayIt is a social media platform designed for language learners to achieve fluency through direct interaction with native speakers. The backend provides a robust infrastructure for real-time video tutoring, social networking, and a secure micro-payment ecosystem.

### 🚀 Key Features
Real-time Language Exchange (WebRTC): High-quality, peer-to-peer video calling for immersive practice, powered by Django Channels signaling.

Persistent Social Chat: Real-time text messaging using WebSockets, allowing students and mentors to share resources and maintain connections.

Atomic Booking System: Prevents double-booking of native speakers using database-level locks (select_for_update).

Secure Wallet System: A built-in virtual economy for seamless credit transfers between learners and mentors upon session completion.

Role-Based Access (JWT): Distinct permissions and profiles for Students (Learners) and Mentors (Native Speakers).

### 🛠️ Tech Stack
Framework: Django REST Framework
Real-time: Django Channels (WebSockets)
Database: PostgreSQL (Recommended) or SQLite
Real-time/WebSockets: Django Channels & Daphne
Containerization: Docker & Docker Compose

### 🧱 Project Structure
sayit_backend/
├── Chat/               # Video signaling & Chat logic
├── user/               # Custom User models & Serializers
├── sayit_backend/      # Main settings & URL routing
├── manage.py
└── Dockerfile