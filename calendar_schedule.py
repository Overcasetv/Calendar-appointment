import tkinter as tk
import customtkinter as ctk
import json
import os
import uuid
import csv
from datetime import datetime, timedelta
from tkinter import messagebox, filedialog
import time
import shutil

# Set the appearance mode for the application
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# --- Define File Paths ---
APPOINTMENTS_FILE = "appointments_data.json"
SETTINGS_FILE = "schedule_settings.json"
CLIENTS_FILE = "clients_data.json"
DOCUMENTS_DIR = "client_documents"

class ScheduleSystem:
    """
    Manages all backend logic for client registration and appointment scheduling.
    This class handles data persistence by reading from and writing to JSON files.
    """
    def __init__(self):
        self.appointments_file = APPOINTMENTS_FILE
        self.settings_file = SETTINGS_FILE
        self.clients_file = CLIENTS_FILE
        self.documents_dir = DOCUMENTS_DIR

        # Create the documents directory if it doesn't exist
        os.makedirs(self.documents_dir, exist_ok=True)

        self.clients = self._load_clients()
        self.settings = self._load_settings()
        self.appointments = self._load_appointments()
        self.run_daily_tasks()

    def _load_clients(self):
        """Loads client data from the JSON file, or initializes an empty list."""
        if os.path.exists(self.clients_file):
            try:
                with open(self.clients_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading client data: {e}. Starting with an empty database.")
                return []
        else:
            print(f"Client database file '{self.clients_file}' not found. Creating a new one.")
            with open(self.clients_file, 'w') as f:
                json.dump([], f)
            return []

    def _save_clients(self):
        """Saves the current state of client data back to the JSON file."""
        with open(self.clients_file, 'w') as f:
            json.dump(self.clients, f, indent=4)

    def _load_settings(self):
        """Loads system settings from a JSON file, or initializes defaults if not found."""
        default_settings = {
            "session_fee": 50.00,
            "time_slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
        }
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    return {**default_settings, **settings}
            except (json.JSONDecodeError, FileNotFoundError):
                print("Error loading settings. Using defaults.")
                return default_settings
        else:
            return default_settings

    def _save_settings(self):
        """Saves the current state of settings back to the JSON file."""
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)
    
    def _load_appointments(self):
        """Loads detailed appointment data from a JSON file."""
        if os.path.exists(self.appointments_file):
            try:
                with open(self.appointments_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []

    def _save_appointments(self):
        """Saves appointment data to a JSON file."""
        with open(self.appointments_file, 'w') as f:
            json.dump(self.appointments, f, indent=4)

    def get_available_slots(self, date_str):
        """Returns a list of all available slots for a given date."""
        all_slots = self.settings.get("time_slots", [])
        booked_slots = [
            app['slot_number'] for app in self.appointments
            if app['date'] == date_str and app['status'] != 'Cancelled'
        ]
        return [slot for slot in all_slots if slot not in booked_slots]
    
    def get_total_slots_global(self):
        """Returns the global total number of appointment slots."""
        return len(self.settings.get("time_slots", []))

    def set_time_slots(self, new_slots):
        """Updates the list of available time slots."""
        self.settings["time_slots"] = new_slots
        self._save_settings()
        return True

    def get_booked_slots(self, date_str):
        """Returns the number of booked slots for a given date."""
        return len([
            app for app in self.appointments
            if app['date'] == date_str and app['status'] != 'Cancelled'
        ])

    def make_appointment(self, date_str, client_id, client_name, slot_number, comment):
        """Creates a single appointment if the slot is available."""
        if slot_number not in self.get_available_slots(date_str):
            return False, f"Slot {slot_number} is not available for this date."
        
        # Add a single detailed appointment record
        new_appointment = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "client_name": client_name,
            "date": date_str,
            "slot_number": slot_number,
            "payment_status": "Unpaid",
            "total_fee": self.get_session_fee(),
            "status": "Booked",
            "comment": comment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.appointments.append(new_appointment)
        self._save_appointments()
        
        return True, "Appointment booked successfully."

    def delete_appointment(self, appointment_id):
        """Deletes a specific appointment."""
        self.appointments = [app for app in self.appointments if app['id'] != appointment_id]
        self._save_appointments()
        return True
    
    def edit_appointment(self, appointment_id, new_date_str, new_slot_number, new_comment):
        """Edits an existing appointment with a new date, slot, and comment."""
        app_to_edit = next((app for app in self.appointments if app['id'] == appointment_id), None)
        
        if not app_to_edit:
            return False, "Appointment not found."
            
        # Check if the new slot is available
        if new_slot_number not in self.get_available_slots(new_date_str) and new_slot_number != app_to_edit['slot_number']:
            return False, f"Slot {new_slot_number} is not available on {new_date_str}."

        app_to_edit['date'] = new_date_str
        app_to_edit['slot_number'] = new_slot_number
        app_to_edit['comment'] = new_comment
        self._save_appointments()
        return True, "Appointment successfully updated."

    def get_all_appointments(self):
        """Returns a list of all detailed appointment records."""
        return self.appointments
    
    def get_report_data(self, start_date_str, end_date_str):
        """Generates a financial report for a date range."""
        try:
            start_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return None

        total_revenue = 0
        total_paid = 0
        total_unpaid = 0
        total_bookings = 0
        
        filtered_appointments = []
        for app in self.appointments:
            app_date_dt = datetime.strptime(app['date'], '%Y-%m-%d')
            
            if start_date_dt <= app_date_dt <= end_date_dt and app['status'] != 'Cancelled':
                filtered_appointments.append(app)
                total_bookings += 1
                total_revenue += app.get('total_fee', 0)
                if app.get('payment_status') == 'Paid':
                    total_paid += app.get('total_fee', 0)
                else:
                    total_unpaid += app.get('total_fee', 0)

        return {
            "total_revenue": total_revenue,
            "total_paid": total_paid,
            "total_unpaid": total_unpaid,
            "total_bookings": total_bookings,
            "appointments": filtered_appointments
        }

    def update_appointment_payment_status(self, appointment_id, status):
        """Updates the payment status of an appointment."""
        app = next((a for a in self.appointments if a['id'] == appointment_id), None)
        if app:
            app['payment_status'] = status
            self._save_appointments()
            return True
        return False
        
    def upload_document_to_client(self, client_id, file_path):
        """Uploads a document to a client's dedicated folder."""
        client = next((c for c in self.clients if c['id'] == client_id), None)
        if not client:
            return False, "Client not found."

        dest_folder = os.path.join(self.documents_dir, client_id)
        os.makedirs(dest_folder, exist_ok=True)
        
        filename = os.path.basename(file_path)
        dest_path = os.path.join(dest_folder, filename)

        try:
            shutil.copy(file_path, dest_path)
            
            new_document = {
                "filename": filename,
                "path": dest_path,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            if 'documents' not in client:
                client['documents'] = []
            client['documents'].append(new_document)
            self._save_clients()
            return True, f"File '{filename}' uploaded successfully."
        except Exception as e:
            return False, f"Error uploading file: {e}"

    def get_client_by_id(self, client_id):
        """Finds a client by their unique ID."""
        return next((client for client in self.clients if client['id'] == client_id), None)
    
    def run_daily_tasks(self):
        """Automatically updates appointment statuses on startup."""
        today = datetime.now().strftime('%Y-%m-%d')

        for app in self.appointments:
            app_date = app.get('date')
            app_status = app.get('status')
            
            if app_date and app_status:
                app_date_dt = datetime.strptime(app_date, '%Y-%m-%d').date()
                today_dt = datetime.strptime(today, '%Y-%m-%d').date()

                if app_date_dt < today_dt and app_status == 'Booked':
                    app['status'] = 'Completed'
                elif app_date_dt == today_dt and app_status == 'Booked':
                    app['status'] = 'Pending'
        self._save_appointments()

    def get_session_fee(self):
        """Retrieves the current session fee."""
        return self.settings.get("session_fee", 50.00)

    def update_session_fee(self, new_fee):
        """Updates and saves the session fee."""
        try:
            fee = float(new_fee)
            self.settings["session_fee"] = fee
            self._save_settings()
            return True
        except ValueError:
            return False

    def register_client(self, client_info: dict):
        """
        Registers a new client with a unique ID and initial status.
        Includes a timestamp.
        """
        now = datetime.now()
        new_client = {
            "id": str(uuid.uuid4()),
            "registration_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "name": client_info.get("name"),
            "dob": client_info.get("dob"),
            "email": client_info.get("email"),
            "cellphone": client_info.get("cellphone"),
            "comments": [],
            "documents": []
        }
        self.clients.append(new_client)
        self._save_clients()
        return new_client

    def add_comment(self, client_id: str, comment: str):
        """Adds a new timestamped comment to a client's record."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for client in self.clients:
            if client['id'] == client_id:
                client['comments'].append({"timestamp": timestamp, "text": comment})
                self._save_clients()
                return True
        return False

    def update_client(self, client_id: str, new_info: dict):
        """Updates the details for a specific client."""
        for i, client in enumerate(self.clients):
            if client["id"] == client_id:
                self.clients[i].update(new_info)
                self._save_clients()
                return True
        return False

    def delete_client(self, client_id: str):
        """Deletes a client from the system by their unique ID."""
        initial_count = len(self.clients)
        self.clients = [client for client in self.clients if client['id'] != client_id]
        if len(self.clients) < initial_count:
            self._save_clients()
            return True
        return False

    def update_payment(self, client_id: str, amount: float):
        """Updates the payment status for a specific client."""
        for client in self.clients:
            if client["id"] == client_id:
                comment = f"Received payment of ${amount:.2f}."
                self.add_comment(client_id, comment)
                self._save_clients()
                return True
        return False

    def get_all_clients(self):
        """Returns the list of all registered clients."""
        return self.clients
    
    def get_client_by_name_or_email(self, query: str):
        """Searches for clients by name or email."""
        query = query.lower()
        results = [
            client for client in self.clients
            if query in client.get("name", "").lower() or query in client.get("email", "").lower()
        ]
        return results

    def export_appointments_to_csv(self, file_path):
        """Exports all appointment data to a CSV file."""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'client_name', 'date', 'slot_number', 'payment_status', 'total_fee', 'status', 'comment', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for app in self.appointments:
                    app_to_write = {key: app.get(key, 'N/A') for key in fieldnames}
                    writer.writerow(app_to_write)
            return True
        except Exception as e:
            print(f"Error exporting appointments to CSV: {e}")
            return False

    def export_clients_to_csv(self, file_path):
        """Exports all client data to a CSV file."""
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'registration_date', 'name', 'dob', 'email', 'cellphone', 'comments', 'documents']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for client in self.clients:
                    comments_string = "\n".join([f"[{c['timestamp']}] {c['text']}" for c in client.get('comments', [])])
                    documents_string = "\n".join([f"[{d['timestamp']}] {d['filename']}" for d in client.get('documents', [])])
                    client_to_write = {
                        'id': client.get('id', 'N/A'),
                        'registration_date': client.get('registration_date', 'N/A'),
                        'name': client.get('name', 'N/A'),
                        'dob': client.get('dob', 'N/A'),
                        'email': client.get('email', 'N/A'),
                        'cellphone': client.get('cellphone', 'N/A'),
                        'comments': comments_string,
                        'documents': documents_string
                    }
                    writer.writerow(client_to_write)
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
            
    def export_daily_report_to_csv(self, file_path):
        """Exports the current day's report data to a CSV file."""
        today = datetime.now().strftime('%Y-%m-%d')
        report_data = self.get_report_data(today, today)

        if not report_data or not report_data['appointments']:
            return False, "No data to export for today."
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'client_name', 'date', 'slot_number', 'payment_status', 'total_fee', 'status', 'comment']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for app in report_data['appointments']:
                    writer.writerow({
                        'id': app.get('id'),
                        'client_name': app.get('client_name'),
                        'date': app.get('date'),
                        'slot_number': app.get('slot_number'),
                        'payment_status': app.get('payment_status'),
                        'total_fee': app.get('total_fee'),
                        'status': app.get('status'),
                        'comment': app.get('comment', '')
                    })
            return True, "Report exported successfully."
        except Exception as e:
            print(f"Error exporting daily report: {e}")
            return False, f"An error occurred: {e}"

# --- Splash Screen Class ---
class SplashScreen(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Loading...")
        self.geometry("400x250")
        self.resizable(False, False)
        self.overrideredirect(True)

        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (self.winfo_width() // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content_frame = ctk.CTkFrame(self, fg_color=ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        content_frame.pack(expand=True, fill="both", padx=10, pady=10)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure((0,1,2,3), weight=1)

        ctk.CTkLabel(content_frame, text="Appointment Scheduler", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=(20,5), sticky="s")
        ctk.CTkLabel(content_frame, text="Application Loading...", font=ctk.CTkFont(size=16)).grid(row=1, column=0, pady=(5,10))
        ctk.CTkLabel(content_frame, text="📅", font=ctk.CTkFont(size=40)).grid(row=2, column=0, pady=10)

        self.progress_bar = ctk.CTkProgressBar(content_frame, orientation="horizontal", width=250)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=3, column=0, pady=(10,20), sticky="n")

        self.progress_value = 0
        self.animate_progress()

    def animate_progress(self):
        if self.progress_value < 1:
            self.progress_value += 0.05
            self.progress_bar.set(self.progress_value)
            self.after(50, self.animate_progress)
        else:
            self.destroy()

class App(ctk.CTk):
    """
    Main application window and GUI.
    """
    def __init__(self, backend_system):
        super().__init__()
        self.backend = backend_system

        self.title("Appointment Scheduler")
        self.geometry("800x600")
        self.resizable(False, False)
        self.withdraw()
        
        self.splash_screen = SplashScreen(self)
        self.splash_screen.update()

        time.sleep(2)

        self.splash_screen.destroy()
        self.deiconify()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self, width=760, height=560, command=self.on_tab_change)
        self.tab_view.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_view.add("Dashboard") 
        self.tab_view.add("Appointments")
        self.tab_view.add("Registration")
        self.tab_view.add("Client List")
        self.tab_view.add("Check-in")
        self.tab_view.add("Reports")

        self.setup_dashboard_tab()
        self.setup_appointments_tab()
        self.setup_registration_tab()
        self.setup_client_list_tab()
        self.setup_checkin_tab()
        self.setup_reports_tab()
        
    def on_tab_change(self, selected_tab_name):
        if selected_tab_name == "Appointments":
            self.render_appointments_list()
        elif selected_tab_name == "Dashboard":
            self.refresh_dashboard()
        elif selected_tab_name == "Reports":
            self.refresh_reports_tab()
        elif selected_tab_name == "Client List":
            self.render_clients()
        elif selected_tab_name == "Check-in":
            for widget in self.checkin_results_frame.winfo_children():
                widget.destroy()

    def setup_dashboard_tab(self):
        """Sets up the UI for the Dashboard tab with a calendar and appointment controls."""
        dashboard_tab = self.tab_view.tab("Dashboard")
        dashboard_tab.grid_columnconfigure(0, weight=1)
        dashboard_tab.grid_columnconfigure(1, weight=1)
        dashboard_tab.grid_rowconfigure(1, weight=1)
        
        time_slot_frame = ctk.CTkFrame(dashboard_tab)
        time_slot_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="nw")
        ctk.CTkLabel(time_slot_frame, text="Set Time Slots:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10, pady=5)
        self.time_slots_entry = ctk.CTkEntry(time_slot_frame, width=400, placeholder_text="Enter comma-separated times (e.g., 09:00, 09:30, 10:00)")
        self.time_slots_entry.pack(side="left", padx=5)
        update_time_slots_button = ctk.CTkButton(time_slot_frame, text="Set Slots", width=80, command=self.update_time_slots)
        update_time_slots_button.pack(side="left", padx=5)

        calendar_frame = ctk.CTkFrame(dashboard_tab)
        calendar_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        calendar_frame.grid_columnconfigure(0, weight=1)

        self.calendar_header_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        self.calendar_header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.prev_month_button = ctk.CTkButton(self.calendar_header_frame, text="<", width=30, command=lambda: self.prev_month())
        self.prev_month_button.pack(side="left", padx=(0, 5))
        
        self.month_year_label = ctk.CTkLabel(self.calendar_header_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
        self.month_year_label.pack(side="left", expand=True)
        
        self.next_month_button = ctk.CTkButton(self.calendar_header_frame, text=">", width=30, command=lambda: self.next_month())
        self.next_month_button.pack(side="right", padx=(5, 0))
        
        self.calendar_grid = ctk.CTkFrame(calendar_frame)
        self.calendar_grid.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.current_date = datetime.now()
        
        self.draw_calendar()
        self.refresh_dashboard()

    def update_time_slots(self):
        """Updates the time slots based on user input."""
        slots_str = self.time_slots_entry.get()
        if not slots_str:
            messagebox.showerror("Error", "Please enter at least one time slot.")
            return

        new_slots = [s.strip() for s in slots_str.split(',') if s.strip()]
        if not all(self.is_valid_time_format(s) for s in new_slots):
            messagebox.showerror("Error", "Invalid time format. Please use HH:MM format (e.g., 09:00, 14:30).")
            return
            
        if self.backend.set_time_slots(new_slots):
            messagebox.showinfo("Success", "Time slots updated successfully.")
            self.refresh_dashboard()
        else:
            messagebox.showerror("Error", "Failed to update time slots.")

    def is_valid_time_format(self, time_str):
        """Checks if a string is in HH:MM format."""
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False

    def setup_appointments_tab(self):
        """Sets up the UI for the Appointments tab."""
        appointments_tab = self.tab_view.tab("Appointments")
        appointments_tab.grid_columnconfigure(0, weight=1)
        appointments_tab.grid_rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(appointments_tab, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_frame, text="Scheduled Appointments", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, padx=(10, 0), sticky="w")
        
        search_frame = ctk.CTkFrame(appointments_tab, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.appointment_search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by client name...")
        self.appointment_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.appointment_search_entry.bind("<Return>", self.filter_appointments)
        
        search_button = ctk.CTkButton(search_frame, text="Search", command=lambda: self.filter_appointments(None), width=100)
        search_button.grid(row=0, column=1, padx=(0, 10))

        self.export_appointments_button = ctk.CTkButton(search_frame, text="Export to CSV", command=self.export_appointments_csv, width=120)
        self.export_appointments_button.grid(row=0, column=2, padx=(0, 0))

        self.appointments_list_frame = ctk.CTkScrollableFrame(appointments_tab)
        self.appointments_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.render_appointments_list()

    def filter_appointments(self, event):
        query = self.appointment_search_entry.get().lower()
        all_appointments = self.backend.get_all_appointments()
        if query:
            filtered_appointments = [app for app in all_appointments if query in app.get('client_name', '').lower()]
            self.render_appointments_list(filtered_appointments)
        else:
            self.render_appointments_list(all_appointments)

    def setup_reports_tab(self):
        """Sets up the UI for the Reports tab."""
        reports_tab = self.tab_view.tab("Reports")
        reports_tab.grid_columnconfigure(0, weight=1)
        reports_tab.grid_rowconfigure(1, weight=1)
        
        report_controls_frame = ctk.CTkFrame(reports_tab, fg_color="transparent")
        report_controls_frame.grid(row=0, column=0, pady=(10, 20), sticky="n")
        
        ctk.CTkLabel(report_controls_frame, text="Financial Reports", font=ctk.CTkFont(size=24, weight="bold")).pack(side="top", pady=(0, 10))
        
        date_controls_frame = ctk.CTkFrame(report_controls_frame, fg_color="transparent")
        date_controls_frame.pack(side="top")

        self.start_date_entry = ctk.CTkEntry(date_controls_frame, placeholder_text="Start Date (YYYY-MM-DD)")
        self.start_date_entry.pack(side="left", padx=10)
        self.end_date_entry = ctk.CTkEntry(date_controls_frame, placeholder_text="End Date (YYYY-MM-DD)")
        self.end_date_entry.pack(side="left", padx=10)
        
        generate_button = ctk.CTkButton(date_controls_frame, text="Generate Report", command=lambda: self.generate_report())
        generate_button.pack(side="left", padx=10)
        
        export_daily_button = ctk.CTkButton(report_controls_frame, text="Export Today's Report to CSV", command=self.export_daily_report_csv)
        export_daily_button.pack(pady=10)

        self.reports_frame = ctk.CTkScrollableFrame(reports_tab)
        self.reports_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

    def export_appointments_csv(self):
        """Prompts for file path and exports appointments to CSV."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="appointments_data.csv"
        )
        if file_path:
            if self.backend.export_appointments_to_csv(file_path):
                messagebox.showinfo("Success", f"Appointments successfully exported to {file_path}")
            else:
                messagebox.showerror("Error", "Failed to export appointments to CSV.")

    def export_daily_report_csv(self):
        """Prompts for file path and exports today's report to CSV."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"daily_report_{datetime.now().strftime('%Y-%m-%d')}.csv"
        )
        if file_path:
            success, message = self.backend.export_daily_report_to_csv(file_path)
            if success:
                messagebox.showinfo("Success", message)
            else:
                messagebox.showerror("Error", message)

    def draw_calendar(self):
        """Draws the calendar grid for the current month."""
        for widget in self.calendar_grid.winfo_children():
            widget.destroy()

        self.month_year_label.configure(text=self.current_date.strftime("%B %Y"))
        
        days_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, day in enumerate(days_of_week):
            label = ctk.CTkLabel(self.calendar_grid, text=day, font=ctk.CTkFont(weight="bold"))
            label.grid(row=0, column=i, padx=5, pady=5)
            self.calendar_grid.grid_columnconfigure(i, weight=1)
        
        first_day_of_month = self.current_date.replace(day=1)
        start_day_of_week = first_day_of_month.weekday()
        
        days_in_month = (self.current_date.replace(month=self.current_date.month % 12 + 1, day=1) - timedelta(days=1)).day if self.current_date.month != 12 else 31
        
        row, col = 1, start_day_of_week
        
        for day_num in range(1, days_in_month + 1):
            date_obj = first_day_of_month.replace(day=day_num)
            day_str = date_obj.strftime("%Y-%m-%d")
            
            total_slots = self.backend.get_total_slots_global()
            available_slots = len(self.backend.get_available_slots(day_str))
            
            if total_slots > 0:
                text_color = "black"
                if available_slots == 0:
                    bg_color = "red"
                elif available_slots / total_slots < 0.25:
                    bg_color = "orange"
                else:
                    bg_color = "#E0E0E0"  # Soft gray for available days
            else:
                bg_color = "gray"
                text_color = "black"
            
            day_button = ctk.CTkButton(self.calendar_grid, text=f"{day_num}\nSlots: {available_slots}/{total_slots}", 
                                      command=lambda d=date_obj.date(): self.select_date(d),
                                      fg_color=bg_color,
                                      text_color=text_color,
                                      hover_color="#C8C8C8" if bg_color == "#E0E0E0" else bg_color)
            
            day_button.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
            
            col += 1
            if col > 6:
                col = 0
                row += 1
    
    def select_date(self, date):
        """Opens a new window to make an appointment for a specific date."""
        total_slots = self.backend.get_total_slots_global()

        if total_slots == 0:
            messagebox.showerror("Error", "Please set the time slots on the Dashboard first.")
            return
        
        self.open_appointment_window(date)

    def open_appointment_window(self, date):
        """Creates a new window for making an appointment."""
        appointment_window = ctk.CTkToplevel(self)
        appointment_window.title(f"Book Appointment on {date.strftime('%Y-%m-%d')}")
        appointment_window.geometry("400x550")
        
        self.update_idletasks()
        app_x = self.winfo_x()
        app_y = self.winfo_y()
        app_width = self.winfo_width()
        app_height = self.winfo_height()
        
        win_width = 400
        win_height = 550
        x = app_x + (app_width // 2) - (win_width // 2)
        y = app_y + (app_height // 2) - (win_height // 2)
        appointment_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
        
        ctk.CTkLabel(appointment_window, text=f"Book Appointment for: {date.strftime('%B %d, %Y')}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        slot_frame = ctk.CTkFrame(appointment_window, fg_color="transparent")
        slot_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(slot_frame, text="Select Time Slot:").pack(side="left", padx=(0, 5))
        available_slots = self.backend.get_available_slots(date.strftime('%Y-%m-%d'))
        self.slot_optionmenu = ctk.CTkOptionMenu(slot_frame, values=available_slots if available_slots else ["No Slots Available"])
        self.slot_optionmenu.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(appointment_window, text="Add a Comment (optional):", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.comment_entry = ctk.CTkTextbox(appointment_window, height=80, width=350)
        self.comment_entry.pack(padx=20, pady=5)

        search_frame = ctk.CTkFrame(appointment_window, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(15, 5))
        self.search_entry_app = ctk.CTkEntry(search_frame, placeholder_text="Search clients...")
        self.search_entry_app.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(appointment_window, text="Select a Client:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        
        client_list_frame = ctk.CTkScrollableFrame(appointment_window, height=150)
        client_list_frame.pack(fill="x", padx=20, pady=5)

        self.selected_client_id = None
        radio_var = tk.StringVar(value="")
        
        def on_client_select():
            self.selected_client_id = radio_var.get()
            
        def filter_client_list_app(event):
            query = self.search_entry_app.get().lower()
            filtered_clients = [
                client for client in self.backend.get_all_clients()
                if query in client.get('name', '').lower()
            ]
            self.populate_client_list(filtered_clients, client_list_frame, radio_var, on_client_select)

        self.search_entry_app.bind("<KeyRelease>", filter_client_list_app)

        all_clients = self.backend.get_all_clients()
        if not all_clients:
            ctk.CTkLabel(client_list_frame, text="No clients found. Please register a client first.").pack(pady=10)
        else:
            self.populate_client_list(all_clients, client_list_frame, radio_var, on_client_select)

        def confirm_appointment():
            if not self.selected_client_id:
                messagebox.showerror("Error", "Please select a client.")
                return

            date_str = date.strftime('%Y-%m-%d')
            slot_number = self.slot_optionmenu.get()
            appointment_comment = self.comment_entry.get("1.0", "end-1c")
            if slot_number == "No Slots Available":
                messagebox.showerror("Error", "No slots available for the selected date.")
                return
            
            selected_client = next((c for c in self.backend.get_all_clients() if c['id'] == self.selected_client_id), None)
            
            if selected_client:
                success, message = self.backend.make_appointment(date_str, selected_client['id'], selected_client['name'], slot_number, appointment_comment)
            else:
                success, message = False, "Client not found."

            if success:
                messagebox.showinfo("Success", f"Appointment confirmed for {selected_client['name']} in slot {slot_number}.")
                appointment_window.destroy()
                self.refresh_dashboard()
                self.render_appointments_list()
            else:
                messagebox.showerror("Error", f"Could not book appointment: {message}")

        confirm_button = ctk.CTkButton(appointment_window, text="Confirm Appointment", command=confirm_appointment)
        confirm_button.pack(pady=20)
        
    def open_edit_appointment_window(self, appointment):
        """Creates a new window to edit an existing appointment."""
        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Edit Appointment for {appointment['client_name']}")
        edit_window.geometry("400x400")

        self.update_idletasks()
        app_x = self.winfo_x()
        app_y = self.winfo_y()
        app_width = self.winfo_width()
        app_height = self.winfo_height()

        win_width = 400
        win_height = 400
        x = app_x + (app_width // 2) - (win_width // 2)
        y = app_y + (app_height // 2) - (win_height // 2)
        edit_window.geometry(f"{win_width}x{win_height}+{x}+{y}")

        ctk.CTkLabel(edit_window, text=f"Editing: {appointment['client_name']}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(edit_window, text=f"Original Date: {appointment['date']}").pack(pady=5)
        ctk.CTkLabel(edit_window, text=f"Original Slot: {appointment['slot_number']}").pack(pady=5)
        
        new_date_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        new_date_frame.pack(pady=5)
        ctk.CTkLabel(new_date_frame, text="New Date (YYYY-MM-DD):").pack(side="left")
        new_date_entry = ctk.CTkEntry(new_date_frame)
        new_date_entry.insert(0, appointment['date'])
        new_date_entry.pack(side="left")

        new_slot_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        new_slot_frame.pack(pady=5)
        ctk.CTkLabel(new_slot_frame, text="New Slot:").pack(side="left")
        
        all_slots = self.backend.settings.get("time_slots", [])
        new_slot_optionmenu = ctk.CTkOptionMenu(new_slot_frame, values=all_slots)
        new_slot_optionmenu.set(appointment['slot_number'])
        new_slot_optionmenu.pack(side="left")

        ctk.CTkLabel(edit_window, text="Comment:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        new_comment_entry = ctk.CTkTextbox(edit_window, height=80, width=350)
        new_comment_entry.insert("1.0", appointment.get('comment', ''))
        new_comment_entry.pack(padx=20, pady=5)


        def update_appointment_action():
            new_date_str = new_date_entry.get()
            new_slot_number = new_slot_optionmenu.get()
            new_comment = new_comment_entry.get("1.0", "end-1c")

            success, message = self.backend.edit_appointment(appointment['id'], new_date_str, new_slot_number, new_comment)
            if success:
                messagebox.showinfo("Success", "Appointment successfully updated.")
                edit_window.destroy()
                self.render_appointments_list()
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", f"Failed to update appointment: {message}")
        
        save_button = ctk.CTkButton(edit_window, text="Save Changes", command=update_appointment_action)
        save_button.pack(pady=20)

    def update_appointment_payment_status_action(self, appointment_id, edit_window):
        """Updates the payment status for an appointment and refreshes the UI."""
        if self.backend.update_appointment_payment_status(appointment_id, "Paid"):
            messagebox.showinfo("Success", "Payment status updated to Paid.")
            edit_window.destroy()
            self.render_appointments_list()
            self.refresh_reports_tab()
        else:
            messagebox.showerror("Error", "Failed to update payment status.")
    
    def populate_client_list(self, clients, parent_frame, radio_var, on_select_command):
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        for client in clients:
            radio_button = ctk.CTkRadioButton(parent_frame, text=client.get("name"), variable=radio_var, value=client.get("id"), command=on_select_command)
            radio_button.pack(anchor="w", padx=10, pady=5)
            
    def prev_month(self):
        """Moves the calendar to the previous month."""
        first_day_of_prev_month = self.current_date.replace(day=1) - timedelta(days=1)
        self.current_date = first_day_of_prev_month.replace(day=1)
        self.draw_calendar()
        
    def next_month(self):
        """Moves the calendar to the next month."""
        last_day_of_current_month = self.current_date.replace(day=28) + timedelta(days=4)
        self.current_date = last_day_of_current_month.replace(day=1)
        self.draw_calendar()
        
    def refresh_dashboard(self):
        """Refreshes the data displayed in the dashboard."""
        self.draw_calendar()
        total_slots = self.backend.get_total_slots_global()
        current_slots = ", ".join(self.backend.settings.get("time_slots", []))
        self.time_slots_entry.delete(0, tk.END)
        self.time_slots_entry.insert(0, current_slots)
        
    def render_appointments_list(self, appointments_to_display=None):
        """Renders the list of active appointments on the new tab, sorted by date and time."""
        for widget in self.appointments_list_frame.winfo_children():
            widget.destroy()

        all_appointments = appointments_to_display if appointments_to_display is not None else self.backend.get_all_appointments()

        if not all_appointments:
            ctk.CTkLabel(self.appointments_list_frame, text="No appointments found.").pack(pady=20)
            return

        # Sort appointments first by date, then by time slot
        sorted_appointments = sorted(all_appointments, key=lambda app: (app['date'], app['slot_number']))

        # Group appointments by date
        appointments_by_date = {}
        for app in sorted_appointments:
            date_str = app['date']
            if date_str not in appointments_by_date:
                appointments_by_date[date_str] = []
            appointments_by_date[date_str].append(app)

        # Render the appointments with date headings
        for date_str, app_list in appointments_by_date.items():
            date_frame = ctk.CTkFrame(self.appointments_list_frame, fg_color="transparent")
            date_frame.pack(fill="x", pady=(15, 5))
            ctk.CTkLabel(date_frame, text=f"Appointments on {date_str}:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

            for app in app_list:
                try:
                    appointment_card = ctk.CTkFrame(self.appointments_list_frame)
                    appointment_card.pack(pady=5, padx=10, fill="x")

                    status_colors = {
                        "Booked": "blue",
                        "Pending": "orange",
                        "Completed": "green",
                        "Cancelled": "red"
                    }

                    status_mark = ctk.CTkFrame(appointment_card, width=15, height=15, corner_radius=10, fg_color=status_colors.get(app.get('status'), "blue"))
                    status_mark.pack(side="left", padx=(10, 5))

                    details_frame = ctk.CTkFrame(appointment_card, fg_color="transparent")
                    details_frame.pack(side="left", fill="x", expand=True)

                    ctk.CTkLabel(details_frame, text=f"Client: {app.get('client_name', 'N/A')}", font=ctk.CTkFont(weight="bold")).pack(pady=2, anchor="w")
                    ctk.CTkLabel(details_frame, text=f"Time Slot: {app.get('slot_number', 'N/A')}", anchor="w").pack(pady=2, anchor="w")
                    ctk.CTkLabel(details_frame, text=f"Status: {app.get('status', 'N/A')}", anchor="w").pack(pady=2, anchor="w")
                    ctk.CTkLabel(details_frame, text=f"Payment: {app.get('payment_status', 'N/A')} | Fee: ${app.get('total_fee', 0):.2f}", anchor="w").pack(pady=2, anchor="w")
                    
                    comment_text = app.get('comment', '')
                    if comment_text:
                        ctk.CTkLabel(details_frame, text=f"Comment: {comment_text}", anchor="w", wraplength=450).pack(pady=2, anchor="w")

                    actions_frame = ctk.CTkFrame(appointment_card, fg_color="transparent")
                    actions_frame.pack(side="right", padx=10, pady=10)

                    edit_button = ctk.CTkButton(actions_frame, text="Edit", width=70, command=lambda app=app: self.open_edit_appointment_window(app))
                    edit_button.pack(pady=5)
                    
                    delete_button = ctk.CTkButton(actions_frame, text="Delete", fg_color="red", hover_color="#c42c2c", width=70,
                                                command=lambda app_id=app['id']: self.delete_appointment_action(app_id))
                    delete_button.pack(pady=5)
                except KeyError as e:
                    print(f"Skipping malformed appointment entry due to missing key: {e}")
                    continue

    def delete_appointment_action(self, app_id):
        """Handles the deletion of a specific appointment."""
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this appointment? This cannot be undone."):
            if self.backend.delete_appointment(app_id):
                messagebox.showinfo("Success", "Appointment successfully deleted.")
                self.render_appointments_list()
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", "Could not delete appointment.")
    
    def refresh_reports_tab(self):
        """Refreshes the reports tab with default or existing date range."""
        for widget in self.reports_frame.winfo_children():
            widget.destroy()

        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()

        if start_date_str and end_date_str:
            self.generate_report()
        else:
            ctk.CTkLabel(self.reports_frame, text="Enter a date range and click 'Generate Report'.").pack(pady=20)


    def setup_registration_tab(self):
        """Sets up the UI elements for the Registration tab."""
        registration_tab = self.tab_view.tab("Registration")
        registration_tab.grid_columnconfigure(0, weight=1)
        
        self.header_label = ctk.CTkLabel(registration_tab, text="Client Registration", font=ctk.CTkFont(size=24, weight="bold"))
        self.header_label.pack(pady=10)
        
        form_frame = ctk.CTkFrame(registration_tab, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="x", expand=True)

        ctk.CTkLabel(form_frame, text="Register New Client", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        self.name_entry = ctk.CTkEntry(form_frame, placeholder_text="Full Name")
        self.name_entry.pack(pady=5, padx=10, fill="x")
        
        self.dob_entry = ctk.CTkEntry(form_frame, placeholder_text="Date of Birth (YYYY-MM-DD)")
        self.dob_entry.pack(pady=5, padx=10, fill="x")

        self.email_entry = ctk.CTkEntry(form_frame, placeholder_text="Email Address")
        self.email_entry.pack(pady=5, padx=10, fill="x")

        self.cellphone_entry = ctk.CTkEntry(form_frame, placeholder_text="Cellphone")
        self.cellphone_entry.pack(pady=5, padx=10, fill="x")

        self.register_button = ctk.CTkButton(form_frame, text="Register Client", command=lambda: self.register_client())
        self.register_button.pack(pady=15, padx=10, fill="x")

        export_button = ctk.CTkButton(form_frame, text="Export Clients to CSV", command=self.export_clients_csv)
        export_button.pack(pady=(10, 0))

    def setup_client_list_tab(self):
        """Sets up the UI elements for the Client List tab."""
        client_list_tab = self.tab_view.tab("Client List")
        client_list_tab.grid_columnconfigure(0, weight=1)
        client_list_tab.grid_rowconfigure(1, weight=1)

        search_frame = ctk.CTkFrame(client_list_tab, fg_color="transparent")
        search_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by name or email...")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.search_button = ctk.CTkButton(search_frame, text="Search", command=self.search_clients)
        self.search_button.grid(row=0, column=1, padx=10, pady=10)
        
        self.export_button = ctk.CTkButton(search_frame, text="Export to CSV", command=self.export_clients_csv)
        self.export_button.grid(row=0, column=2, padx=10, pady=10)
        
        self.list_frame = ctk.CTkScrollableFrame(client_list_tab)
        self.list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        self.render_clients()
        
    def setup_checkin_tab(self):
        """Sets up the UI elements for the Check-in tab."""
        checkin_tab = self.tab_view.tab("Check-in")
        checkin_tab.grid_columnconfigure(0, weight=1)
        
        header_frame = ctk.CTkFrame(checkin_tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(header_frame, text="Check-in & Payments", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        export_button = ctk.CTkButton(header_frame, text="Export Clients to CSV", command=self.export_clients_csv)
        export_button.pack(side="right")
        
        search_frame = ctk.CTkFrame(checkin_tab, fg_color="transparent")
        search_frame.pack(padx=20, pady=10, fill="x")
        ctk.CTkLabel(search_frame, text="Search Client:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
        self.checkin_search_entry = ctk.CTkEntry(search_frame, placeholder_text="Enter name or email...")
        self.checkin_search_entry.pack(side="left", expand=True, fill="x", padx=5)
        self.checkin_search_button = ctk.CTkButton(search_frame, text="Search", command=self.search_checkin_client)
        self.checkin_search_button.pack(side="left", padx=5)

        self.checkin_results_frame = ctk.CTkScrollableFrame(checkin_tab)
        self.checkin_results_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        fees_frame = ctk.CTkFrame(checkin_tab)
        fees_frame.pack(padx=20, pady=(10, 20), fill="x")
        ctk.CTkLabel(fees_frame, text="Session Fee", font=ctk.CTkFont(weight="bold")).pack(pady=(5,10))
        
        session_fee_frame = ctk.CTkFrame(fees_frame, fg_color="transparent")
        session_fee_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(session_fee_frame, text="Fee ($):").pack(side="left", padx=(0, 5))
        self.session_fee_entry = ctk.CTkEntry(session_fee_frame, width=80)
        self.session_fee_entry.insert(0, str(self.backend.get_session_fee()))
        self.session_fee_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(fees_frame, text="Set Session Fee", command=self.update_session_fee_action).pack(pady=10)

    def update_session_fee_action(self):
        """Handles the 'Set Session Fee' button click."""
        new_fee = self.session_fee_entry.get()
        if self.backend.update_session_fee(new_fee):
            messagebox.showinfo("Success", f"Session fee updated to ${new_fee}.")
        else:
            messagebox.showerror("Error", "Invalid fee entered. Please enter a numerical value.")
            self.session_fee_entry.delete(0, tk.END)
            self.session_fee_entry.insert(0, str(self.backend.get_session_fee()))

    def search_checkin_client(self):
        """Searches for a client and displays a check-in interface."""
        query = self.checkin_search_entry.get()
        if not query:
            messagebox.showerror("Error", "Please enter a name or email to search.")
            return

        for widget in self.checkin_results_frame.winfo_children():
            widget.destroy()

        results = self.backend.get_client_by_name_or_email(query)
        
        if not results:
            ctk.CTkLabel(self.checkin_results_frame, text="No clients found.").pack(pady=20)
            return

        for client in results:
            self.create_checkin_card(self.checkin_results_frame, client)

    def create_checkin_card(self, parent_frame, client):
        """Creates a UI card for a client to perform a check-in."""
        client_card = ctk.CTkFrame(parent_frame, fg_color="gray20" if ctk.get_appearance_mode() == "Dark" else "gray85")
        client_card.pack(pady=10, padx=10, fill="x")
        client_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(client_card, text=f"Client: {client['name']}", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(5,0), padx=10, sticky="w")
        ctk.CTkLabel(client_card, text=f"Email: {client['email']}", anchor="w", padx=10).grid(row=1, column=0, pady=(0,5), padx=10, sticky="w")
        
        active_app = next((app for app in self.backend.get_all_appointments() if app['client_id'] == client['id'] and app['status'] == 'Pending'), None)

        if active_app:
            app_frame = ctk.CTkFrame(client_card)
            app_frame.grid(row=2, column=0, padx=10, pady=(10,5), sticky="ew")
            app_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(app_frame, text="Pending Appointment Found!", font=ctk.CTkFont(weight="bold")).pack(pady=5)
            ctk.CTkLabel(app_frame, text=f"Date: {active_app['date']}").pack(anchor="w", padx=10)
            ctk.CTkLabel(app_frame, text=f"Time Slot: {active_app['slot_number']}").pack(anchor="w", padx=10)
            
            checkin_button = ctk.CTkButton(app_frame, text="Mark as Completed & Paid", command=lambda app_id=active_app['id']: self.mark_appointment_paid(app_id))
            checkin_button.pack(pady=10)
        else:
             ctk.CTkLabel(client_card, text="No pending appointments found.", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, pady=10, sticky="w")
        
    def mark_appointment_paid(self, app_id):
        """Marks a pending appointment as completed and paid."""
        app = next((a for a in self.backend.get_all_appointments() if a['id'] == app_id), None)
        if app and app['status'] == 'Pending':
            if messagebox.askyesno("Confirm Payment", f"Mark appointment on {app['date']} as Paid?"):
                self.backend.update_appointment_payment_status(app_id, "Paid")
                self.backend.add_comment(app['client_id'], f"Payment of ${app['total_fee']:.2f} received for appointment on {app['date']}.")
                messagebox.showinfo("Success", "Appointment marked as paid and completed.")
                self.search_checkin_client()
                self.render_appointments_list()
        else:
            messagebox.showerror("Error", "This appointment is not pending or does not exist.")
            
    def search_clients(self):
        """Filters and renders the list of clients based on the search query."""
        query = self.search_entry.get().lower()
        all_clients = self.backend.get_all_clients()
        
        if not query:
            self.render_clients(all_clients)
        else:
            filtered_clients = [
                client for client in all_clients
                if query in client.get('name', '').lower() or
                   query in client.get('email', '').lower()
            ]
            self.render_clients(filtered_clients)

    def register_client(self):
        """Handles the registration button click."""
        name = self.name_entry.get()
        dob = self.dob_entry.get()
        email = self.email_entry.get()
        cellphone = self.cellphone_entry.get()
        
        if not name or not email or not dob or not cellphone:
            messagebox.showerror("Error", "All fields are required.")
            return
            
        client_info = {
            "name": name,
            "dob": dob,
            "email": email,
            "cellphone": cellphone
        }
        
        self.backend.register_client(client_info)
        messagebox.showinfo("Success", f"Client {name} registered successfully!")
        self.name_entry.delete(0, tk.END)
        self.dob_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.cellphone_entry.delete(0, tk.END)
        self.render_clients()
        self.tab_view.set("Client List")

    def render_clients(self, clients_to_display=None):
        """Renders the list of clients in the GUI."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        clients = clients_to_display if clients_to_display is not None else self.backend.get_all_clients()

        if not clients:
            ctk.CTkLabel(self.list_frame, text="No clients found.").pack(pady=20)
            return

        for client in clients:
            client_card = ctk.CTkFrame(self.list_frame)
            client_card.pack(pady=10, padx=10, fill="x")
            
            details_frame = ctk.CTkFrame(client_card, fg_color="transparent")
            details_frame.pack(side="left", padx=10, pady=10, fill="x", expand=True)

            ctk.CTkLabel(details_frame, text=f"Name: {client.get('name', 'N/A')}", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x")
            ctk.CTkLabel(details_frame, text=f"DOB: {client.get('dob', 'N/A')}", anchor="w").pack(fill="x")
            ctk.CTkLabel(details_frame, text=f"Email: {client.get('email', 'N/A')}", anchor="w").pack(fill="x")
            ctk.CTkLabel(details_frame, text=f"Cellphone: {client.get('cellphone', 'N/A')}", anchor="w").pack(fill="x")
            ctk.CTkLabel(details_frame, text=f"Registered: {client.get('registration_date', 'N/A')}", anchor="w").pack(fill="x")
            
            comments_frame = ctk.CTkFrame(details_frame)
            comments_frame.pack(fill="x", pady=(10, 5))
            ctk.CTkLabel(comments_frame, text="Comments Log:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            
            for comment in client.get("comments", []):
                ctk.CTkLabel(comments_frame, text=f"[{comment.get('timestamp', 'N/A')}] {comment.get('text', 'N/A')}", anchor="w", wraplength=450).pack(fill="x")

            actions_frame = ctk.CTkFrame(client_card, fg_color="transparent")
            actions_frame.pack(side="right", padx=10, pady=10)

            add_comment_button = ctk.CTkButton(actions_frame, text="Add Comment", command=lambda id=client['id']: self.open_comment_window(id))
            add_comment_button.pack(pady=5)
            
            edit_button = ctk.CTkButton(actions_frame, text="Edit", command=lambda client=client: self.open_edit_client_window(client))
            edit_button.pack(pady=5)
            
            upload_doc_button = ctk.CTkButton(actions_frame, text="Upload Documents", command=lambda client_id=client['id']: self.open_upload_documents_window(client_id))
            upload_doc_button.pack(pady=5)
            
            delete_button = ctk.CTkButton(actions_frame, text="Delete", fg_color="red", hover_color="#c42c2c", command=lambda id=client['id']: self.delete_client(id))
            delete_button.pack(pady=5)

    def open_edit_client_window(self, client):
        """Opens a new window to edit client details."""
        edit_window = ctk.CTkToplevel(self)
        edit_window.title(f"Edit {client['name']}")
        edit_window.geometry("400x300")

        self.update_idletasks()
        app_x = self.winfo_x()
        app_y = self.winfo_y()
        app_width = self.winfo_width()
        app_height = self.winfo_height()

        win_width = 400
        win_height = 300
        x = app_x + (app_width // 2) - (win_width // 2)
        y = app_y + (app_height // 2) - (win_height // 2)
        edit_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
        
        ctk.CTkLabel(edit_window, text=f"Editing: {client['name']}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        fields = {
            "Name": "name",
            "DOB": "dob",
            "Email": "email",
            "Cellphone": "cellphone"
        }
        
        entries = {}
        for label, key in fields.items():
            frame = ctk.CTkFrame(edit_window, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(frame, text=f"{label}:", width=120, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame)
            entry.insert(0, client.get(key, ""))
            entry.pack(side="right", expand=True, fill="x")
            entries[key] = entry
            
        def save_changes():
            updated_info = {key: entries[key].get() for key in entries}
            self.backend.update_client(client['id'], updated_info)
            messagebox.showinfo("Success", "Client details updated.")
            self.render_clients()
            edit_window.destroy()

        save_button = ctk.CTkButton(edit_window, text="Save Changes", command=save_changes)
        save_button.pack(pady=20)
    
    def open_comment_window(self, client_id):
        """Opens a new window to add a comment."""
        comment_window = ctk.CTkToplevel(self)
        comment_window.title("Add Comment")
        comment_window.geometry("400x200")

        self.update_idletasks()
        app_x = self.winfo_x()
        app_y = self.winfo_y()
        app_width = self.winfo_width()
        app_height = self.winfo_height()

        win_width = 400
        win_height = 200
        x = app_x + (app_width // 2) - (win_width // 2)
        y = app_y + (app_height // 2) - (win_height // 2)
        comment_window.geometry(f"{win_width}x{win_height}+{x}+{y}")

        ctk.CTkLabel(comment_window, text="Enter your comment:", font=ctk.CTkFont(size=16)).pack(pady=10)
        
        comment_entry = ctk.CTkTextbox(comment_window, height=80, width=350)
        comment_entry.pack(padx=20, pady=10)
        
        def save_comment():
            comment_text = comment_entry.get("1.0", "end-1c")
            if comment_text:
                if self.backend.add_comment(client_id, comment_text):
                    messagebox.showinfo("Success", "Comment added successfully.")
                    self.render_clients()
                    comment_window.destroy()
                else:
                    messagebox.showerror("Error", "Could not add comment.")
            else:
                messagebox.showerror("Error", "Comment cannot be empty.")

        save_button = ctk.CTkButton(comment_window, text="Save Comment", command=save_comment)
        save_button.pack(pady=10)

    def open_upload_documents_window(self, client_id):
        """Opens a window to upload documents for a specific client."""
        upload_window = ctk.CTkToplevel(self)
        upload_window.title("Upload Documents")
        upload_window.geometry("500x400")

        self.update_idletasks()
        app_x = self.winfo_x()
        app_y = self.winfo_y()
        app_width = self.winfo_width()
        app_height = self.winfo_height()
        win_width = 500
        win_height = 400
        x = app_x + (app_width // 2) - (win_width // 2)
        y = app_y + (app_height // 2) - (win_height // 2)
        upload_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
        
        current_client = next((client for client in self.backend.get_all_clients() if client['id'] == client_id), None)
        if not current_client:
            messagebox.showerror("Error", "Client not found.")
            upload_window.destroy()
            return
        
        ctk.CTkLabel(upload_window, text=f"Documents for Client: {current_client['name']}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        doc_frame = ctk.CTkFrame(upload_window, fg_color="transparent")
        doc_frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))
        
        ctk.CTkLabel(doc_frame, text="Current Files:", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        doc_list_frame = ctk.CTkScrollableFrame(doc_frame, height=150)
        doc_list_frame.pack(fill="x", pady=5)
        
        def refresh_doc_list():
            for widget in doc_list_frame.winfo_children():
                widget.destroy()
            
            for doc in current_client.get('documents', []):
                ctk.CTkLabel(doc_list_frame, text=f"[{doc['timestamp']}] {doc['filename']}", anchor="w").pack(fill="x")
        
        refresh_doc_list()

        upload_controls_frame = ctk.CTkFrame(upload_window, fg_color="transparent")
        upload_controls_frame.pack(fill="x", padx=20, pady=10)

        def browse_and_upload():
            file_path = filedialog.askopenfilename(
                title="Select a file to upload",
                filetypes=[("All Files", "*.*"), ("Image Files", "*.png;*.jpg;*.jpeg"), ("PDF Files", "*.pdf")]
            )
            if file_path:
                success, message = self.backend.upload_document_to_client(client_id, file_path)
                if success:
                    messagebox.showinfo("Success", message)
                    refresh_doc_list()
                else:
                    messagebox.showerror("Error", message)

        upload_button = ctk.CTkButton(upload_controls_frame, text="Browse & Upload File", command=browse_and_upload)
        upload_button.pack(fill="x")

    def delete_client(self, client_id):
        """Handles the "Delete" button click with a confirmation dialog."""
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this client's record?"):
            if self.backend.delete_client(client_id):
                messagebox.showinfo("Success", "Client record deleted.")
                self.render_clients()
            else:
                messagebox.showerror("Error", "Could not delete client record.")

    def export_clients_csv(self):
        """Handles the "Export to CSV" button click."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="clients_data.csv"
        )
        if file_path:
            if self.backend.export_clients_to_csv(file_path):
                messagebox.showinfo("Success", f"Data successfully exported to {file_path}")
            else:
                messagebox.showerror("Error", "Failed to export data to CSV.")
    
    def generate_report(self):
        """Generates and displays a financial report."""
        start_date_str = self.start_date_entry.get()
        end_date_str = self.end_date_entry.get()

        if not start_date_str or not end_date_str:
            messagebox.showerror("Error", "Please enter both a start and end date.")
            return

        report_data = self.backend.get_report_data(start_date_str, end_date_str)

        if report_data is None:
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
            return

        for widget in self.reports_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.reports_frame, text=f"Financial Report: {start_date_str} to {end_date_str}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.reports_frame, text=f"Total Revenue: ${report_data['total_revenue']:.2f}").pack(anchor="w", padx=20)
        ctk.CTkLabel(self.reports_frame, text=f"Total Paid: ${report_data['total_paid']:.2f}").pack(anchor="w", padx=20)
        ctk.CTkLabel(self.reports_frame, text=f"Total Unpaid: ${report_data['total_unpaid']:.2f}").pack(anchor="w", padx=20)
        ctk.CTkLabel(self.reports_frame, text=f"Total Bookings: {report_data['total_bookings']}").pack(anchor="w", padx=20)
        
        ctk.CTkLabel(self.reports_frame, text="--- Detailed Appointments ---", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        if report_data['appointments']:
            for app in report_data['appointments']:
                app_card = ctk.CTkFrame(self.reports_frame)
                app_card.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(app_card, text=f"Client: {app['client_name']}", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10)
                ctk.CTkLabel(app_card, text=f"Date: {app['date']} | Slot: {app['slot_number']}").pack(anchor="w", padx=10)
                ctk.CTkLabel(app_card, text=f"Payment: {app['payment_status']} | Fee: ${app['total_fee']:.2f}").pack(anchor="w", padx=10)
                comment_text = app.get('comment', '')
                if comment_text:
                    ctk.CTkLabel(app_card, text=f"Comment: {comment_text}", anchor="w", wraplength=450).pack(padx=10)
        else:
            ctk.CTkLabel(self.reports_frame, text="No appointments in this date range.").pack()
            
if __name__ == "__main__":
    print("Starting the Appointment Scheduler app...")
    try:
        system = ScheduleSystem()
        app = App(system)
        app.mainloop()
        print("Application closed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An error occurred: {e}")