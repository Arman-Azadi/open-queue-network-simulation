# Open Queueing Network Simulation (DES & Analytical)
**Author:** Arman Azadi
**Institution:** Iran University of Science and Technology (IUST)

## 📌 Project Overview
This project is a comprehensive tool for analyzing the performance of **Open Queueing Networks** (specifically Jackson Networks). It implements two distinct approaches to solve for system performance metrics:
1.  **Discrete Event Simulation (DES):** A custom simulation engine built from scratch to model packet flow, queuing, and service events.
2.  **Analytical Solution:** A mathematical solver using **Jackson's Theorem** and traffic equations to calculate exact theoretical values.

The tool features a **Graphical User Interface (GUI)** built with `tkinter`, allowing users to dynamically configure network parameters and visualize the comparison between simulated and analytical results.

## 🔬 Methodology

### 1. System Topology
The system models a **4-Node Open Queue Network** where:
* Jobs (packets) arrive from outside following a **Poisson Process**.
* Service times at each node follow an **Exponential Distribution**.
* Routing between nodes is probabilistic (Markovian routing).

### 2. Analytical Approach (Jackson Network)
The solver calculates the exact steady-state performance using the **Traffic Equations**:
$$\lambda_i = \gamma_i + \sum_{j=1}^{N} \lambda_j P_{ji}$$
Where:
* $\lambda_i$: Total arrival rate to node $i$
* $\gamma_i$: External arrival rate
* $P_{ji}$: Routing probability from node $j$ to $i$

It computes metrics such as **Utilization ($\rho$)**, **Mean Queue Length ($L_q$)**, and **Mean Response Time ($W$)**.

### 3. Discrete Event Simulation (DES)
The simulation logic is implemented without external simulation libraries. It manages:
* **Event Calendar:** Scheduling arrivals and service completions.
* **State Variables:** Tracking the number of jobs in each queue.
* **Statistics Collection:** aggregating wait times and utilizations over the simulation clock.

## 📊 Features & Results
* **Interactive GUI:** Users can input arrival rates, service rates, and the routing probability matrix.
* **Validation:** The tool automatically compares Simulation results vs. Analytical results to validate the DES implementation.
* **Detailed Reporting:** Displays key performance indicators (KPIs) for every node in the network.

*(See `Performance_Analysis_Report.pdf` for the detailed mathematical derivation and error analysis between the two methods.)*

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **GUI Framework:** `tkinter` (Standard Python Library)
* **Libraries:** `random` (for stochastic generation), `math`.

## 🚀 Usage
1.  Clone the repository:
    ```bash
    git clone [https://github.com/armanazadi/open-queue-network-simulation.git](https://github.com/armanazadi/open-queue-network-simulation.git)
    ```
2.  Run the GUI application:
    ```bash
    python simulation_gui.py
    ```
