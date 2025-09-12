Appointment Scheduler Application
This is a desktop application built with Python and CustomTkinter for managing an appointment schedule. It allows you to set up a calendar, define specific time slots, register clients, book appointments, and generate financial reports.

Features
Dashboard: A calendar view that shows daily appointment availability.

Time Slots: The ability to define custom, reusable time slots for each day (e.g., "09:00", "10:30").

Client Management: A system to register new clients and view, edit, or delete existing client records. You can also upload documents and add comments to each client's profile.

Appointment Booking: Book appointments for specific clients on available dates and times. Each appointment can include a custom comment.

Real-time Updates: The application updates the calendar and appointment lists in real-time as new bookings are made.

Financial Reports: Generate and export financial reports for a specified date range, including total revenue, paid vs. unpaid fees, and a detailed list of appointments.

Data Persistence: All client and appointment data is automatically saved to local JSON files (.json files are created in the same folder), so your information is saved between sessions.

Prerequisites
To run this application, you need to have Python 3.6 or higher installed on your system.

You also need to install the customtkinter library, which provides the modern graphical user interface.

Setup
Install the dependency: Open your terminal or command prompt and run the following command to install customtkinter:

pip install customtkinter

Save the code: Save the provided Python code into a file named appointment_scheduler.py.

How to Run the Application
Open your terminal or command prompt.

Navigate to the directory where you saved the appointment_scheduler.py file.

Run the following command:

python appointment_scheduler.py

The application window will appear, and you can start managing your appointments.

Data Files
The application automatically creates and manages the following data files in the same directory:

clients_data.json: Stores all registered client information.

appointments_data.json: Stores all booked appointments.

schedule_settings.json: Stores your custom time slots and session fee.

client_documents/: A folder for any documents uploaded for a client.

These files ensure your data is persistent. Do not modify these files manually while the application is running.