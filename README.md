# Molecule Generator

![molecule-thumb](https://github.com/user-attachments/assets/70886d9a-f2bc-4e4b-ac66-b579ab3bf562)

**Author:** The French Monkey (TFMSTYLE)  
**Version:** 1.0.0  

---

## Overview

The Molecule Generator creates procedural 3D molecular structures using predefined atomic layouts.  
It includes a comprehensive library of chemical presets — from simple molecules like water or methane to complex biological and crystalline models such as DNA fragments, graphene, or hemoglobin.  
Each atom is represented as a colored sphere and each bond as a cylinder, automatically joined and shaded for clean, unified geometry.  
Ideal for scientific visualization, stylized renders, or educational demonstrations.

---

## Parameters

### Live Update
When enabled, automatically rebuilds the selected molecule object whenever a parameter changes.  
Useful for interactive tweaking, though performance may decrease for heavy structures.

---

### Preset
Defines the molecular or structural model to generate.  
Available options include a wide range of categories:

- **Simple Molecules:** H₂O, CH₄, CO₂, NH₃  
- **Organic Compounds:** Ethanol, Acetic Acid, Benzene, Formaldehyde, Acetone  
- **Biological Molecules:** Glycine, ATP, DNA Fragment, Alpha Helix, Protein Tube  
- **Macromolecules & Complexes:** Caffeine, Hemoglobin, Chlorophyll, Penicillin, Vitamin C  
- **Allotropes & Lattices:** Graphene, Diamond, Fullerene C₆₀, Carbon Nanotube, Carbon Cage  
- **Crystals & Materials:** NaCl, Quartz Lattice, BCC/FCC Metal Lattices, Salt Crystal  

Each preset defines atom positions and bond connections according to simplified molecular geometry.

---

### Global Scale
Controls the overall size of the generated molecule.  
Affects both atom positions and bond lengths proportionally.

---

### Atom Radius Scale
Scales the covalent radii used for the atom spheres.  
Adjust to fine-tune the visual balance between atoms and bonds.

---

### Bond Radius
Defines the radius of the cylinders used to represent molecular bonds.  
Larger values make connections appear thicker.

---

### Atom Segments
Sets the sphere resolution for atoms.  
Higher values produce smoother atoms but increase polygon count.

---

### Bond Segments
Sets the cylinder resolution for bonds.  
Higher values create rounder, smoother connections.

---

### Smooth Shading
Applies smooth shading across all joined geometry.  
Produces a polished look suitable for rendering, especially for organic forms.

---

## Operators

### Generate Molecule
Creates a new molecule based on the selected preset and parameters, or regenerates the active one if it was produced by the Molecule Generator.  
Automatically applies element-based coloring and material assignment.

---

## Usage Notes

- Enable **Live Update** to adjust parameters interactively.  
- Adjust **Global Scale**, **Atom Radius Scale**, and **Bond Radius** to match visual style or unit scale.  
- Increase **Atom Segments** and **Bond Segments** for higher-quality output when rendering.  
- Generated geometry is fully manifold, joined, and ready for shading or export.  
- Each atom is colored automatically based on its element (H, C, N, O, S, etc.).  
- Use Blender’s **Auto Smooth** or modifiers for refined visual results.  
- Presets are simplified and intended for visualization — not for chemical accuracy or measurement.
