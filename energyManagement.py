import numpy as np
import matplotlib.pyplot as plt

# ----------------------------
# 1. Simulation Setup
# ----------------------------
dt = 1.0                   # time step (seconds)
total_time = 1800          # total simulation time in seconds (e.g., 30 minutes)
time_array = np.arange(0, total_time, dt)

# Example drive cycle (kW demand over time)
# In a real model, you'd use a standard drive cycle like UDDS, WLTP, etc.
# For now, let's create a pseudo-random demand profile:
np.random.seed(42)
power_demand_profile = np.abs(np.random.normal(15, 10, len(time_array)))  
# Clip the negative values
power_demand_profile = np.clip(power_demand_profile, 0, 40)  

# Vehicle speed profile (m/s)
# Just a rough example: random fluctuation around city speeds
speed_profile = np.abs(np.random.normal(13, 5, len(time_array)))  # ~ 47 km/h average
speed_profile = np.clip(speed_profile, 0, 30)  # limit to 108 km/h

# ----------------------------
# 2. Battery Model (Simplified)
# ----------------------------
battery_capacity_kWh = 10.0
battery_capacity_Wh = battery_capacity_kWh * 1000.0  # Wh
battery_voltage = 200.0  # V nominal
# Convert capacity to Coulombs: 1 Wh = 3600 Coulombs at 1 Volt
battery_capacity_C = battery_capacity_Wh * 3600 / battery_voltage

# Initial SoC
SoC_init = 0.7

# Battery internal parameters (simplified)
battery_internal_resistance = 0.05  # ohms, example
# This can be used to estimate I^2*R losses or voltage drop if desired

# ----------------------------
# 3. Control Logic Thresholds
# ----------------------------
SoC_High = 0.8
SoC_Low = 0.3
SoC_Cruise = 0.5
Power_Demand_Threshold = 20.0  # kW
Max_Electric_Power = 30.0      # kW, motor limit

# For regenerative braking (simplified):
regen_efficiency = 0.3  # 30% of braking power is recaptured
# We'll just assume that negative power demand in the profile
# could represent braking, or we do a separate approach.

# State Machine: 0 = EV Mode, 1 = Hybrid/Assist, 2 = Engine Only
mode_labels = ["EV Mode", "Hybrid", "Engine Only"]

# ----------------------------
# 4. Simulation Variables
# ----------------------------
SoC_array = np.zeros_like(time_array)
mode_array = np.zeros_like(time_array, dtype=int)
engine_power_array = np.zeros_like(time_array)  # kW from engine
motor_power_array = np.zeros_like(time_array)   # kW from motor
battery_power_array = np.zeros_like(time_array) # net battery power (positive = discharge)

SoC = SoC_init
current_mode = 0  # start in EV Mode, if possible

for i, t in enumerate(time_array):
    demand = power_demand_profile[i]  # kW
    speed = speed_profile[i]          # m/s

    # --- Determine Mode ---
    if SoC > SoC_High and demand < Max_Electric_Power:
        # High SoC, demand is within motor capability -> EV Mode
        current_mode = 0
    elif SoC < SoC_Low:
        # Low SoC -> engine must run
        current_mode = 2
    else:
        # Middle ground -> use Hybrid mode if demand is high
        if demand > Power_Demand_Threshold:
            current_mode = 1
        else:
            # If demand is below threshold, prefer EV
            current_mode = 0

    # --- Calculate Power Split ---
    if current_mode == 0:
        # EV Mode
        # Motor supplies 'demand' if possible
        if demand <= Max_Electric_Power:
            motor_power = demand
            engine_power = 0.0
        else:
            motor_power = Max_Electric_Power
            # If demand is beyond motor capacity, engine has to supply remainder
            engine_power = demand - Max_Electric_Power

    elif current_mode == 1:
        # Hybrid Mode
        # Engine + Motor together
        # Let's assume engine meets half of the demand, motor meets the other half (example strategy).
        engine_power = demand / 2.0
        motor_power = min(demand / 2.0, Max_Electric_Power)

    else:  # current_mode == 2
        # Engine Only
        engine_power = demand
        motor_power = 0.0

    # --- Battery Interaction ---
    # Positive motor_power means battery discharging.
    # Negative motor_power (not in this simplified logic, but could happen if regen) means charging.
    battery_power = motor_power  # kW
    # Convert kW to kJ/s = kW * 1000 J/s, then to Coulombs used per second at battery_voltage
    # 1 Joule = 1 Coulomb * 1 Volt
    power_in_watts = battery_power * 1000.0
    if battery_power > 0:
        # Discharge
        dQ = power_in_watts * dt / battery_voltage
        # SoC decreases
        SoC -= dQ / battery_capacity_C
    else:
        # Charge (regen scenario)
        # If motor_power < 0, that means negative demand on motor -> regen
        # We'll keep it simple for now, but you can add regen logic
        pass

    # Ensure SoC stays in [0, 1]
    SoC = max(0.0, min(1.0, SoC))

    # --- Save Data ---
    SoC_array[i] = SoC
    mode_array[i] = current_mode
    engine_power_array[i] = engine_power
    motor_power_array[i] = motor_power
    battery_power_array[i] = battery_power

# ----------------------------
# 5. Visualization
# ----------------------------
plt.figure(figsize=(12,8))

plt.subplot(3,1,1)
plt.plot(time_array, power_demand_profile, label="Power Demand (kW)", color='blue')
plt.plot(time_array, engine_power_array, label="Engine Power (kW)", color='red', linestyle='--')
plt.plot(time_array, motor_power_array, label="Motor Power (kW)", color='green', linestyle='-.')
plt.title("Power Demand vs. Engine/Motor Output")
plt.xlabel("Time (s)")
plt.ylabel("Power (kW)")
plt.legend()

plt.subplot(3,1,2)
plt.plot(time_array, SoC_array, label="Battery SoC", color='magenta')
plt.ylim([0,1])
plt.title("Battery State of Charge")
plt.xlabel("Time (s)")
plt.ylabel("SoC (0-1)")
plt.legend()

plt.subplot(3,1,3)
plt.plot(time_array, mode_array, label="Mode", color='black')
plt.yticks([0,1,2], mode_labels)
plt.title("Operating Mode")
plt.xlabel("Time (s)")
plt.ylabel("Mode")
plt.legend()

plt.tight_layout()
plt.show()