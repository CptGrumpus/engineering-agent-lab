within ;
package EngLab "Engineering agent lab models (Modelica Standard Library 4.1.0)"

  model MSDStep "1-DOF mass-spring-damper, constant force applied from rest at t = 0"
    import Modelica.Mechanics.Translational;

    parameter Real mass_kg = 1.0 "Mass [kg]";
    parameter Real stiffness_N_per_m = 1000.0 "Spring stiffness [N/m]";
    parameter Real damping_ratio = 0.5 "Damping ratio zeta [-]";
    parameter Real step_force_N = 10.0 "Force magnitude [N]";
    parameter Real damping_N_s_per_m = 2*damping_ratio*sqrt(stiffness_N_per_m*mass_kg)
      "Viscous damping coefficient [N.s/m]";

    Translational.Components.Fixed fixed;
    Translational.Components.Spring spring(c = stiffness_N_per_m, s_rel0 = 0);
    Translational.Components.Damper damper(d = damping_N_s_per_m);
    Translational.Components.Mass mass(m = mass_kg, L = 0,
      s(start = 0, fixed = true), v(start = 0, fixed = true));
    Translational.Sources.Force force;
    Modelica.Blocks.Sources.Constant forceSignal(k = step_force_N);

    // Named outputs so the harness can read results without knowing component names.
    Real x_m = mass.s "Displacement [m]";
    Real v_m_per_s = mass.v "Velocity [m/s]";
  equation
    connect(fixed.flange, spring.flange_a);
    connect(fixed.flange, damper.flange_a);
    connect(spring.flange_b, mass.flange_a);
    connect(damper.flange_b, mass.flange_a);
    connect(force.flange, mass.flange_b);
    connect(forceSignal.y, force.f);
  end MSDStep;

end EngLab;
