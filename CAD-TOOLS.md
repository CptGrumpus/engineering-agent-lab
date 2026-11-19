# Open-source CAD and simulation tools for an engineering agent harness

Research carried forward from our discussion on November 18, 2026.

## Purpose

Build a personal environment for practicing engineering automation and preparing for potential contract work. The intended workflow is to translate requirements into models, run analyses, and produce reproducible evidence with an AI coding agent such as Claude Code.

This list includes CAD, simulation, and automation tools. They serve different parts of the workflow; installing all of them is unnecessary.

## Available personal hardware

Reported from the supplied Windows system screenshot:

- AMD Ryzen 9 5900X, 12-core processor.
- 64 GB RAM.
- NVIDIA GeForce RTX 3070, 8 GB VRAM.
- 64-bit Windows on an x64 processor.

Start locally with CAD, systems models, and small engineering simulation examples. Actual performance depends on model size, solver, mesh, and analysis type; this machine has not been benchmarked for these workloads. Measure a representative workload before renting cloud hardware.

Using a hosted AI service does not require hosting its language model on this GPU. Local engineering software and hosted AI access are separate parts of the setup.

## 1. FreeCAD + CalculiX: visual CAD and structural simulation

**Use for:** parametric parts, brackets, housings, stiffness, deflection, and structural analysis practice.

- FreeCAD supplies the CAD interface and FEM workbench.
- CalculiX performs the finite element calculations. FreeCAD's Windows distribution includes CalculiX.
- FreeCAD exposes Python functionality for macros and automation.
- An agent can help create geometry, prepare analysis inputs, run repeatable cases, and extract results. Exact automation coverage should be established with a small working example.

**First exercise:** a simple cantilever beam with documented dimensions, material, supports, and load. Compare displacement against an analytical reference and examine mesh convergence before trying a more complicated bracket.

**Review focus:** units, geometry, material properties, load direction, constraints, reaction balance, convergence, and stress singularities.

Sources: [FreeCAD features and Python support](https://www.freecad.org/features.php), [official FEM tutorial](https://blog.freecad.org/2025/09/16/getting-started-with-fem/), [CalculiX](https://www.dhondt.de/).

## 2. CadQuery: CAD defined in Python

**Use for:** agent-generated parametric parts, dimension sweeps, repeatable geometry, and STEP exports.

- Models are Python source files, making them straightforward for a coding agent to edit and rerun.
- CadQuery supports parametric solid modeling and exports formats including STEP and STL.
- A separate viewer or editor provides visual inspection.
- CadQuery generates geometry; stress and fluid calculations require separate analysis tools.

**First exercise:** generate a mounting plate with a configurable hole pattern, export STEP, and check dimensions and volume across several parameter sets.

**Review focus:** valid solids, parameter limits, dimensions, exports, and whether the geometry matches the intended requirement.

Sources: [CadQuery introduction](https://cadquery.readthedocs.io/en/latest/intro.html), [installation documentation](https://cadquery.readthedocs.io/en/latest/installation.html).

## 3. OpenModelica + OMPython: systems and multiphysics models

**Use for:** system behavior over time, mechanical dynamics, thermal networks, electrical components, and controls.

- OpenModelica provides a Modelica modeling and simulation environment with Windows support.
- The Modelica Standard Library includes mechanical, thermal, electrical, and other components.
- OMPython provides a Python interface for running models and varying parameters.
- This may be the closest fit to the current requirements-to-model workflow if the existing work involves systems and controls rather than detailed 3D analysis.

**First exercise:** a simple thermal network or mass-spring-damper model. Define a measurable requirement, run parameter variations, and compare against a known reference response.

**Review focus:** equations, units, initial conditions, conservation, solver tolerances, and requirement pass/fail criteria.

Sources: [OpenModelica](https://openmodelica.org/), [Modelica Standard Library](https://build.openmodelica.org/Documentation/Modelica.html), [OMPython documentation](https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/ompython.html).

## 4. Python + SciPy: custom models and workflow automation

**Use for:** small mathematical models, differential equations, parameter studies, result processing, and automated requirement checks.

- Python scripts can connect requirements, engineering tools, and result checks.
- SciPy supplies numerical methods, including differential equation solvers.
- Some useful workflows can start here without a full CAD or FEA package.

**First exercise:** simulate a mass-spring-damper system, export the response, and compare it with a reference case. Record the assumptions and numerical settings.

**Review focus:** equation formulation, units, numerical tolerances, reference agreement, and reproducibility.

Source: [SciPy differential equation solver documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html).

## 5. OpenFOAM: computational fluid dynamics

**Use for:** fluid flow and heat-transfer simulation when the project calls for CFD.

- Cases use files and command-line execution that an agent can help prepare and run.
- The official Windows instructions use Windows Subsystem for Linux.
- Introduce it after the basic harness works, or when a specific fluids task justifies the additional setup.

**First exercise:** an established tutorial case with a known reference, followed by a controlled parameter change.

**Review focus:** boundary conditions, mesh quality, physical models, residuals, conservation, convergence, and reference agreement.

Source: [official OpenFOAM Windows guidance](https://openfoam.org/download/windows/).

## Supporting tool to add when needed

**Gmsh** generates finite element meshes and supports Python, command-line execution, and Windows. FreeCAD commonly includes it; check the selected distribution before installing it separately. Source: [Gmsh](https://gmsh.info/) and the [FreeCAD FEM tutorial](https://blog.freecad.org/2025/09/16/getting-started-with-fem/).

## Recommended starting paths

Choose one path for the first working example:

- **Systems and controls:** OpenModelica + OMPython, with Python for checks and reporting.
- **CAD and structural analysis:** FreeCAD + CalculiX; add CadQuery later if Python-defined geometry would help.
- **Workflow automation without detailed geometry:** Python + SciPy first.

Keep OpenFOAM for a specific CFD need. These engineering tools have no software license purchase cost; hosted AI subscriptions or API usage and optional cloud compute are separate expenses. Review the relevant software licenses when packaging or distributing a harness.

## How the agent should participate

1. Turn the problem statement into explicit inputs, assumptions, and measurable requirements.
2. Write readable scripts or native model/input files using documented interfaces.
3. Run the installed engineering tools and retain their logs and outputs.
4. Execute independent checks against a reference or stated acceptance criteria.
5. Produce an evidence summary for human review, including failed checks and limitations.

A completed solver run is not evidence that the model represents the real product. Benchmarks and convergence checks establish parts of numerical verification; physical validation requires suitable experimental or reference data.

## Contract-work fit

Before using a prepared workflow on a paid task, establish the required software and native file formats, whether AI assistance is allowed, the expected validation evidence, and who supplies licenses or compute if proprietary tools are mandatory.

Use public or synthetic practice problems. Keep employer and client models, data, credentials, and licensed environments outside this personal preparation project unless their use is explicitly authorized.

## Current setup status

This document is a researched shortlist. It does not establish that any listed software is installed, that an agent integration works, or that a future client accepts these tools.
