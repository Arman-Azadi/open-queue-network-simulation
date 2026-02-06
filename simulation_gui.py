import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random

# ==========================================
# 1. CONFIGURATION (Stable Parameters)
# ==========================================
LAMBDA_SOURCE_RATE = 4   # Mean Inter-arrival = 0.25
MU_RATES = {
    1: 5,    # Queue 1
    2: 3,    # Queue 2
    3: 3,    # Queue 3
    4: 5     # Queue 4
}

PROBS = {
    '1_to_2': 0.4,
    '1_to_3': 0.6,
    '4_exit': 0.9,
    '4_to_3': 0.1
}

MAX_COMPLETED = 50000      # Valid customers to collect AFTER warm-up (Increased for accuracy)
WARM_UP_CUSTOMERS = 1000   # Number of customers to discard at start

# ==========================================
# 2. SIMULATION LOGIC
# ==========================================
class Customer:
    def __init__(self, id, arrival_time):
        self.id = id
        self.arrival_time = arrival_time

class Event:
    def __init__(self, time, type, customer=None, queue_id=None):
        self.time = time
        self.type = type 
        self.customer = customer
        self.queue_id = queue_id
    
    def __lt__(self, other):
        return self.time < other.time

class SimulationModel:
    def __init__(self):
        self.reset()

    def reset(self):
        self.clock = 0.0
        self.events = []
        self.queues = {1: [], 2: [], 3: [], 4: []}
        self.server_busy = {1: False, 2: False, 3: False, 4: False}
        
        # Stats
        self.stats = {i: {
            'L_accum': 0, 'Q_accum': 0, 'Busy_accum': 0, 
            'Arrivals': 0, 'Departures': 0
        } for i in range(1, 5)}
        
        self.completed_count = 0
        self.total_response_time = 0
        self.last_update = 0.0
        self.cust_counter = 1
        
        # Warm-up tracking
        self.warmup_count = 0
        self.is_warming_up = True
        self.steady_start_time = 0.0  # Time when warm-up finishes
        
        first_arrival = Event(random.expovariate(LAMBDA_SOURCE_RATE), 'ARRIVAL', Customer(1, 0), 1)
        self.schedule(first_arrival)

    def schedule(self, event):
        self.events.append(event)
        self.events.sort()

    def update_accumulators(self):
        # If we are warming up, DO NOT calculate areas. Just update the timestamp.
        if self.is_warming_up:
            self.last_update = self.clock
            return
        
        # Normal Calculation (Only happens AFTER warm-up)
        delta = self.clock - self.last_update
        
        # Only record stats if we are NOT warming up (or you can track them and reset later)
        # Here we track them, but we will RESET them exactly when warm-up ends.
        for i in range(1, 5):
            n = len(self.queues[i])
            self.stats[i]['L_accum'] += n * delta

            q_len = max(0, n - 1) if self.server_busy[i] else 0
            self.stats[i]['Q_accum'] += q_len * delta

            if self.server_busy[i]:
                self.stats[i]['Busy_accum'] += delta

        self.last_update = self.clock

    def reset_stats_post_warmup(self):
        """Resets all counters to 0 but KEEPS the customers in queues/servers."""
        self.stats = {i: {
            'L_accum': 0, 'Q_accum': 0, 'Busy_accum': 0, 
            'Arrivals': 0, 'Departures': 0
        } for i in range(1, 5)}
        self.completed_count = 0
        self.total_response_time = 0
        self.last_update = self.clock # Start integrals from NOW
        self.is_warming_up = False
        self.steady_start_time = self.clock # Mark the start of steady state

    def step(self):
        if not self.events or self.completed_count >= MAX_COMPLETED:
            return None, "Simulation Finished"

        event = self.events.pop(0)
        self.update_accumulators()
        self.clock = event.time
        
        log_msg = ""
        if event.type == 'ARRIVAL':
            log_msg = self.handle_arrival(event)
            if event.queue_id == 1 and event.customer.id == self.cust_counter:
                self.cust_counter += 1
                nxt_time = self.clock + random.expovariate(LAMBDA_SOURCE_RATE)
                self.schedule(Event(nxt_time, 'ARRIVAL', Customer(self.cust_counter, self.clock), 1))
        
        elif event.type == 'DEPARTURE':
            log_msg = self.handle_departure(event)

        return event, log_msg

    def handle_arrival(self, event):
        q = event.queue_id
        self.queues[q].append(event.customer)
        # We count arrivals, but if we reset stats later, this count resets too
        self.stats[q]['Arrivals'] += 1
        msg = f"Cust {event.customer.id} -> Q{q}"
        if not self.server_busy[q]:
            self.server_busy[q] = True
            svc_time = random.expovariate(MU_RATES[q])
            self.schedule(Event(self.clock + svc_time, 'DEPARTURE', event.customer, q))
        return msg

    def handle_departure(self, event):
        q = event.queue_id
        c = self.queues[q].pop(0)
        self.stats[q]['Departures'] += 1
        msg = f"Cust {c.id} left Q{q}"

        next_q = None
        r = random.random()
        
        if q == 1:
            next_q = 2 if r < PROBS['1_to_2'] else 3
        elif q == 2:
            next_q = 4
        elif q == 3:
            next_q = 4
        elif q == 4:
            if r < PROBS['4_exit']:
                next_q = 'EXIT'
            else:
                next_q = 3

        if next_q == 'EXIT':
            # === WARM-UP LOGIC ===
            if self.is_warming_up:
                self.warmup_count += 1
                msg += " -> EXITED (Warmup)"
                if self.warmup_count >= WARM_UP_CUSTOMERS:
                    self.reset_stats_post_warmup()
                    msg += " [WARM-UP DONE - STATS RESET]"
            else:
                self.completed_count += 1
                self.total_response_time += (self.clock - c.arrival_time)
                msg += " -> EXITED"
        else:
            self.handle_arrival(Event(self.clock, 'ARRIVAL', c, next_q))
            msg += f" -> Moved to Q{next_q}"

        if self.queues[q]:
            self.server_busy[q] = True
            svc_time = random.expovariate(MU_RATES[q])
            nxt_c = self.queues[q][0]
            self.schedule(Event(self.clock + svc_time, 'DEPARTURE', nxt_c, q))
        else:
            self.server_busy[q] = False
            
        return msg

# ==========================================
# 3. GUI IMPLEMENTATION
# ==========================================
class SimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PECS Project - Open Queue Network System (With Warm-up)")
        self.root.state('zoomed') 
        self.model = SimulationModel()
        self.running = False
        self.speed_ms = 30 

        # --- Top: Controls ---
        frame_controls = tk.Frame(root, pady=5, bg="#e8e8e8", relief="raised", bd=2)
        frame_controls.pack(fill="x")
        
        btn_font = ("Segoe UI", 11, "bold")
        tk.Button(frame_controls, text="Next Step >>", command=self.do_step, bg="#ffffff", font=btn_font, width=14).pack(side="left", padx=15)
        self.btn_run = tk.Button(frame_controls, text="Run (Auto)", command=self.toggle_run, bg="#aaddaa", font=btn_font, width=14)
        self.btn_run.pack(side="left", padx=15)
        tk.Button(frame_controls, text="Run (Instant)", command=self.run_instant, bg="#ffcc88", font=btn_font, width=14).pack(side="left", padx=15)
        
        # --- NEW BUTTON HERE ---
        tk.Button(frame_controls, text="Finish & Compare", command=self.finish_and_compare, bg="#ffaa55", font=btn_font, width=18).pack(side="left", padx=15)
        
        tk.Button(frame_controls, text="Show Results", command=self.show_results_window, bg="#88ccff", font=btn_font, width=14).pack(side="left", padx=15)
        
        self.lbl_clock = tk.Label(frame_controls, text="CLOCK: 0.00", font=("Consolas", 18, "bold"), bg="#e8e8e8", fg="#000088")
        self.lbl_clock.pack(side="right", padx=30)

        # --- Middle: Canvas (Left) + Event List (Right) ---
        frame_mid = tk.Frame(root)
        frame_mid.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.canvas = tk.Canvas(frame_mid, bg="white", relief="sunken", borderwidth=2)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        frame_events = tk.LabelFrame(frame_mid, text="Future Event List (FEL)", font=("Segoe UI", 11, "bold"), width=280)
        frame_events.pack(side="right", fill="y", padx=10)
        frame_events.pack_propagate(False) 
        
        self.tree_events = ttk.Treeview(frame_events, columns=("Time", "Type", "Node"), show="headings", height=20)
        self.tree_events.heading("Time", text="Time")
        self.tree_events.heading("Type", text="Type")
        self.tree_events.heading("Node", text="Q")
        self.tree_events.column("Time", width=90)
        self.tree_events.column("Type", width=100)
        self.tree_events.column("Node", width=40)
        self.tree_events.pack(fill="both", expand=True)

        # --- Bottom: Stats Panels ---
        frame_bottom = tk.Frame(root, height=220)
        frame_bottom.pack(fill="x", padx=15, pady=10)
        
        # Left: Queue Stats Table
        frame_q_stats = tk.LabelFrame(frame_bottom, text="System Snapshot & Statistical Counters", font=("Segoe UI", 11, "bold"))
        frame_q_stats.pack(side="left", fill="both", expand=True)
        
        cols = ("Queue", "Status", "N (In Sys)", "Arrivals", "Departures", "Area Q(t)", "Area B(t)")
        self.tree_stats = ttk.Treeview(frame_q_stats, columns=cols, show="headings", height=6)
        for col in cols:
            self.tree_stats.heading(col, text=col)
            self.tree_stats.column(col, width=100, anchor="center")
        self.tree_stats.pack(fill="both", expand=True, padx=5, pady=5)

        # Right: Whole System Live Stats
        frame_sys_stats = tk.LabelFrame(frame_bottom, text="Whole System Live Stats", font=("Segoe UI", 11, "bold"), width=320)
        frame_sys_stats.pack(side="right", fill="both", padx=10)
        frame_sys_stats.pack_propagate(False)
        
        # === NEW WARMUP LABEL ===
        self.lbl_warmup = tk.Label(frame_sys_stats, text="Warm-up: Active (0/100)", font=("Arial", 12, "bold"), fg="red")
        self.lbl_warmup.pack(pady=5)
        # ========================

        self.lbl_sys_n = tk.Label(frame_sys_stats, text="Total N: 0", font=("Arial", 14, "bold"), fg="#333333")
        self.lbl_sys_n.pack(pady=5)
        self.lbl_sys_completed = tk.Label(frame_sys_stats, text="Valid Completed: 0", font=("Arial", 12))
        self.lbl_sys_completed.pack(pady=5)
        self.lbl_sys_arr = tk.Label(frame_sys_stats, text="Total Internal Arrivals: 0", font=("Arial", 11), fg="#666666")
        self.lbl_sys_arr.pack(pady=5)

        self.pos = {
            1: (200, 300),
            2: (600, 150),
            3: (600, 450),
            4: (1000, 300)
        }

        self.draw_network()
        self.update_tables()

    def draw_network(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        if w < 100: w = 1200 
        
        self.canvas.create_rectangle(50, 30, 1150, 550, outline="#999999", dash=(8, 8), width=2)
        self.canvas.create_text(600, 50, text="Open Queue Network System", font=("Arial", 18, "bold"), fill="#424350")

        # Input to Q1
        q1_x, q1_y = self.pos[1]
        self.canvas.create_line(50, q1_y, q1_x - 60, q1_y, arrow=tk.LAST, width=5, fill="black")
        self.canvas.create_text(80, q1_y - 25, text=f"Input λ={LAMBDA_SOURCE_RATE}", font=("Arial", 12, "bold"), fill="#0000AA")

        # Output from Q4
        q4_x, q4_y = self.pos[4]
        self.canvas.create_line(q4_x + 60, q4_y, 1160, q4_y, arrow=tk.LAST, width=5, fill="black")
        self.canvas.create_text(1120, q4_y - 25, text="Output", font=("Arial", 12, "bold"), fill="black")
        self.canvas.create_text(1120, q4_y + 25, text=f"p={PROBS['4_exit']}", font=("Arial", 11))

        # Internal Connections
        connections = [(1, 2, PROBS['1_to_2']), (1, 3, PROBS['1_to_3']), (2, 4, None), (3, 4, None)]
        for s, e, prob in connections:
            x1, y1 = self.pos[s]
            x2, y2 = self.pos[e]
            self.canvas.create_line(x1+60, y1, x2-60, y2, arrow=tk.LAST, width=2.5)
            if prob:
                mx, my = (x1+x2)/2, (y1+y2)/2
                self.canvas.create_text(mx-20, my, text=str(prob), font=("Arial", 12, "bold"))

        # Feedback Q4 -> Q3
        x4, y4 = self.pos[4]
        x3, y3 = self.pos[3]
        self.canvas.create_line(x4+50, y4+50, x4+50, y4+120, x3+40, y3+120, x3+35, y3+50, arrow=tk.LAST, smooth=True, fill="blue", width=3)
        self.canvas.create_text(910, 500, text=f"Feedback p={PROBS['4_to_3']}", fill="blue", font=("Arial", 10, "bold"))

        # Nodes
        for i, (x, y) in self.pos.items():
            is_busy = self.model.server_busy[i]
            color = "#ffe0e0" if is_busy else "#e0ffe0"
            outline = "#cc0000" if is_busy else "#008800"
            self.canvas.create_rectangle(x-60, y-40, x+60, y+40, fill=color, outline=outline, width=3)
            self.canvas.create_text(x, y-25, text=f"Queue {i}", font=("Arial", 14, "bold"))
            self.canvas.create_text(x, y+65, text=f"μ={MU_RATES[i]:.2f}", font=("Arial", 12, "bold"), fill="#880000")
            count = len(self.model.queues[i])
            self.canvas.create_text(x, y+5, text=f"N={count}", font=("Arial", 12))
            dots = "." * min(count, 12) + ("+" if count > 12 else "")
            self.canvas.create_text(x, y+25, text=dots, font=("Courier", 24, "bold"))

    def update_tables(self):
        # Clock
        self.lbl_clock.config(text=f"CLOCK: {self.model.clock:.2f}")

        # FEL
        for item in self.tree_events.get_children(): self.tree_events.delete(item)
        for e in self.model.events[:25]:
            q_str = str(e.queue_id) if e.queue_id else "-"
            self.tree_events.insert("", "end", values=(f"{e.time:.2f}", e.type, q_str))

        # Stats Table
        for item in self.tree_stats.get_children(): self.tree_stats.delete(item)
        stats = self.model.stats
        total_n_sys = 0
        total_arrivals_sys = 0
        
        for i in range(1, 5):
            status = "BUSY" if self.model.server_busy[i] else "IDLE"
            n_total = len(self.model.queues[i])
            total_n_sys += n_total
            total_arrivals_sys += stats[i]['Arrivals']
            
            row = (f"Queue {i}", status, str(n_total), stats[i]['Arrivals'], stats[i]['Departures'],
                   f"{stats[i]['Q_accum']:.2f}", f"{stats[i]['Busy_accum']:.2f}")
            self.tree_stats.insert("", "end", values=row)

        # Side Panel Updates
        if self.model.is_warming_up:
            self.lbl_warmup.config(text=f"Warm-up: Active ({self.model.warmup_count}/{WARM_UP_CUSTOMERS})", fg="red")
        else:
            self.lbl_warmup.config(text="Warm-up: Finished", fg="green")

        self.lbl_sys_n.config(text=f"Current Total N: {total_n_sys}")
        self.lbl_sys_completed.config(text=f"Valid Completed: {self.model.completed_count}")
        self.lbl_sys_arr.config(text=f"Total Internal Arrivals: {total_arrivals_sys}")

    def do_step(self):
        event, msg = self.model.step()
        if not event:
            self.running = False
            self.btn_run.config(text="Run (Auto)")
            messagebox.showinfo("Info", "Simulation Finished.")
            return
        self.draw_network()
        self.update_tables()

    def toggle_run(self):
        if self.running:
            self.running = False
            self.btn_run.config(text="Run (Auto)", bg="#aaddaa")
        else:
            self.running = True
            self.btn_run.config(text="Stop", bg="#ffaaaa")
            self.run_loop()

    def run_loop(self):
        if self.running:
            self.do_step()
            self.root.after(self.speed_ms, self.run_loop)

    def run_instant(self):
        self.running = False
        self.btn_run.config(text="Run (Auto)", bg="#aaddaa")
        while self.model.completed_count < MAX_COMPLETED:
            if not self.model.events: break
            self.model.step()
        self.draw_network()
        self.update_tables()
        messagebox.showinfo("Done", "Instant Simulation Completed!")
        self.show_results_window()

    def finish_and_compare(self):
        """Finishes DES and shows detailed comparison with Analytical in a GUI Table."""
        # 1. Run Simulation to Completion
        self.running = False
        self.btn_run.config(text="Run (Auto)", bg="#aaddaa")
        
        while self.model.completed_count < MAX_COMPLETED:
            if not self.model.events: break
            self.model.step()
        
        self.draw_network()
        self.update_tables()
        
        # 2. Analytical Calculations (Exact)
        lam = LAMBDA_SOURCE_RATE
        # Exact Flow Equations
        L1 = lam
        L2 = 0.4 * L1
        L4 = L1 / 0.9
        L3 = 0.6 * L1 + 0.1 * L4
        
        eff_lam = {1: L1, 2: L2, 3: L3, 4: L4}
        
        ana_metrics = {} 
        total_L_ana = 0
        
        for i in range(1, 5):
            l = eff_lam[i]
            m = MU_RATES[i]
            rho = l / m
            L_val = rho / (1 - rho)
            Lq_val = L_val - rho
            W_val = 1 / (m - l)
            Wq_val = W_val - (1/m)
            
            ana_metrics[i] = {'L': L_val, 'Lq': Lq_val, 'W': W_val, 'Wq': Wq_val, 'Rho': rho}
            total_L_ana += L_val
            
        sys_R_ana = total_L_ana / lam

        # 3. Simulation Calculations
        valid_duration = self.model.clock - self.model.steady_start_time
        if valid_duration <= 0.001: valid_duration = 1.0
        
        sim_metrics = {}
        sim_N = 0
        
        for i in range(1, 5):
            L = self.model.stats[i]['L_accum'] / valid_duration
            Lq = self.model.stats[i]['Q_accum'] / valid_duration
            Rho = self.model.stats[i]['Busy_accum'] / valid_duration
            Thru = self.model.stats[i]['Departures'] / valid_duration
            
            W = L / Thru if Thru > 0 else 0
            Wq = Lq / Thru if Thru > 0 else 0
            
            sim_metrics[i] = {'L': L, 'Lq': Lq, 'W': W, 'Wq': Wq, 'Rho': Rho}
            sim_N += L
        
        sim_R = self.model.total_response_time / max(1, self.model.completed_count)

        # 4. Build GUI Table Window
        win = tk.Toplevel(self.root)
        win.title("Comparison Report - Graphical View")
        win.geometry("800x700")
        
        tk.Label(win, text="Analytical vs Simulation Comparison", font=("Arial", 18, "bold"), pady=15).pack()
        
        # Treeview Setup
        cols = ("Metric", "Analytical", "Simulation", "Error %", "Status")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")
        tree.column("Metric", width=180, anchor="w") # Align metric names to left
        tree.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tags for Coloring
        tree.tag_configure("pass", foreground="green")
        tree.tag_configure("fail", foreground="red")
        tree.tag_configure("header", font=("Arial", 10, "bold"), background="#eeeeee")

        # Helper to Add Rows
        def add_row(metric, ana, sim, is_header=False):
            if is_header:
                tree.insert("", "end", values=(metric, "", "", "", ""), tags=("header",))
                return

            err = abs(sim - ana) / ana * 100 if ana > 0 else 0
            status = "PASS" if err < 10 else "HIGH DEV"
            tag = "pass" if err < 10 else "fail"
            tree.insert("", "end", values=(metric, f"{ana:.4f}", f"{sim:.4f}", f"{err:.2f}%", status), tags=(tag,))

        # --- Populate Table ---
        add_row("SYSTEM WIDE METRICS", 0, 0, True)
        add_row("System Total N", total_L_ana, sim_N)
        add_row("System Response R", sys_R_ana, sim_R)
        
        for i in range(1, 5):
            add_row(f"QUEUE {i} METRICS", 0, 0, True)
            add_row(f"  Q{i} L (Avg Num)", ana_metrics[i]['L'], sim_metrics[i]['L'])
            add_row(f"  Q{i} Lq (Avg Queue)", ana_metrics[i]['Lq'], sim_metrics[i]['Lq'])
            add_row(f"  Q{i} W (Avg Time)", ana_metrics[i]['W'], sim_metrics[i]['W'])
            add_row(f"  Q{i} Wq (Avg Wait)", ana_metrics[i]['Wq'], sim_metrics[i]['Wq'])
            add_row(f"  Q{i} Rho (Util)", ana_metrics[i]['Rho'], sim_metrics[i]['Rho'])

        tk.Button(win, text="Close", command=win.destroy, font=("Arial", 12)).pack(pady=10)

    def show_results_window(self):
        win = tk.Toplevel(self.root)
        win.title("Final Steady-State Metrics (Post Warm-up)")
        win.geometry("1000x550")
        
        tk.Label(win, text="Simulation Results Report", font=("Arial", 20, "bold"), pady=15).pack()
        
        # Calculate valid duration
        valid_duration = self.model.clock - self.model.steady_start_time
        if valid_duration <= 0.001: valid_duration = 1.0 

        tk.Label(win, text=f"Total Clock: {self.model.clock:.2f} | Valid Completed: {self.model.completed_count}", font=("Arial", 14)).pack()

        cols = ("Metric", "Queue 1", "Queue 2", "Queue 3", "Queue 4", "SYSTEM TOTAL")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")
        tree.pack(fill="both", expand=True, padx=25, pady=25)

        stats = self.model.stats
        
        row_L = ["L (Avg Number)"]
        row_Lq = ["Lq (Avg Queue)"]
        row_W = ["W (Avg Time)"]
        row_Wq = ["Wq (Avg Wait)"]
        row_Rho = ["Rho (Util %)"]
        
        total_L_sys = 0
        for i in range(1, 5):
            L = stats[i]['L_accum'] / valid_duration
            Lq = stats[i]['Q_accum'] / valid_duration
            Rho = stats[i]['Busy_accum'] / valid_duration
            thru = stats[i]['Departures'] / valid_duration
            W = L / thru if thru > 0 else 0
            Wq = Lq / thru if thru > 0 else 0
            
            total_L_sys += L
            
            row_L.append(f"{L:.4f}")
            row_Lq.append(f"{Lq:.4f}")
            row_W.append(f"{W:.4f}")
            row_Wq.append(f"{Wq:.4f}")
            row_Rho.append(f"{Rho*100:.2f}%")

        R_sys = self.model.total_response_time / max(1, self.model.completed_count)
        
        row_L.append(f"{total_L_sys:.4f} (N)")
        row_Lq.append("-")
        row_W.append(f"{R_sys:.4f} (R)")
        row_Wq.append("-")
        row_Rho.append("-")

        tree.insert("", "end", values=row_L)
        tree.insert("", "end", values=row_Lq)
        tree.insert("", "end", values=row_W)
        tree.insert("", "end", values=row_Wq)
        tree.insert("", "end", values=row_Rho)
        
        tk.Button(win, text="Close Report", command=win.destroy, font=("Arial", 12), bg="#ffcccc").pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorGUI(root)
    root.mainloop()