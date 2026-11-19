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

  model QuarterCarBump "Linear 2-DOF quarter car crossing a (1 - cos) bump"
    import Modelica.Mechanics.Translational;
    import Modelica.Constants.pi;

    parameter Real sprung_mass_kg = 350 "Quarter body mass [kg]";
    parameter Real unsprung_mass_kg = 45 "Wheel, hub, brake mass [kg]";
    parameter Real suspension_stiffness_N_per_m = 22000 "Wheel-rate spring [N/m]";
    parameter Real damping_N_s_per_m = 1500 "Wheel-rate damper [N.s/m]";
    parameter Real tire_stiffness_N_per_m = 220000 "Tire vertical stiffness [N/m]";
    parameter Real speed_m_per_s = 10 "Vehicle speed [m/s]";
    parameter Real bump_height_m = 0.04 "Bump height [m]";
    parameter Real bump_length_m = 1.0 "Bump length [m]";
    parameter Real bump_duration_s = bump_length_m/speed_m_per_s "Time on bump [s]";

    // Coordinates from static equilibrium; gravity cancels for the linear model.
    Translational.Components.Mass body(m = sprung_mass_kg, L = 0,
      s(start = 0, fixed = true), v(start = 0, fixed = true));
    Translational.Components.Mass wheel(m = unsprung_mass_kg, L = 0,
      s(start = 0, fixed = true), v(start = 0, fixed = true));
    Translational.Components.Spring suspension(c = suspension_stiffness_N_per_m, s_rel0 = 0);
    Translational.Components.Damper damper(d = damping_N_s_per_m);
    Translational.Components.Spring tire(c = tire_stiffness_N_per_m, s_rel0 = 0);
    Translational.Sources.Position road(exact = true);
    Modelica.Blocks.Sources.RealExpression roadProfile(
      y = if time < bump_duration_s
          then 0.5*bump_height_m*(1 - cos(2*pi*time/bump_duration_s)) else 0);

    Real zs_m = body.s "Body displacement [m]";
    Real vs_m_per_s = body.v "Body velocity [m/s]";
    Real zu_m = wheel.s "Wheel displacement [m]";
    Real vu_m_per_s = wheel.v "Wheel velocity [m/s]";
    Real zr_m = road.flange.s "Road displacement [m]";
  equation
    connect(roadProfile.y, road.s_ref);
    connect(road.flange, tire.flange_a);
    connect(tire.flange_b, wheel.flange_a);
    connect(wheel.flange_b, suspension.flange_a);
    connect(suspension.flange_b, body.flange_a);
    connect(wheel.flange_b, damper.flange_a);
    connect(damper.flange_b, body.flange_a);
  end QuarterCarBump;

end EngLab;
