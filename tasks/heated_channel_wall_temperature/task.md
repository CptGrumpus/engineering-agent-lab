# Task: cold-plate channel wall temperature

A cold-plate coolant passage is formed by two parallel plates 1 mm apart, much wider than
the gap. Water enters at 25 °C with a fully developed laminar velocity profile and a mean
velocity of 0.1 m/s. Over a 50 mm length, electronics heat **both** walls with a uniform
heat flux of 30 kW/m² each.

Water properties (constant): density 997 kg/m³, viscosity 0.00089 Pa·s, specific heat
4180 J/(kg·K), thermal conductivity 0.607 W/(m·K).

The wall must stay at or under 45 °C. Determine the coolant temperature rise over the
heated length, the peak wall temperature, and the local Nusselt number (based on the
hydraulic diameter) at the end of the heated length, and whether the wall limit is met.

Answer as JSON:

```json
{
  "coolant_rise_K": 0.0,
  "peak_wall_temperature_C": 0.0,
  "nusselt_at_end_of_heating": 0.0,
  "wall_limit_met": true,
  "method": "one or two sentences"
}
```
