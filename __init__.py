# SPDX-FileCopyrightText: 2025-2026 The French Monkey
# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Molecule",
    "author": "The French Monkey",
    "version": (1, 0, 4),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Molecule",
    "description": "Generate molecules",
    "category": "Add Mesh",
    "license": "GPL-3.0-or-later",
}

import bpy, bmesh, math
from math import sin, cos
from mathutils import Vector, Matrix

try:
    from . import relay_updater
except ImportError:  # the Addon Collection has its own updates
    relay_updater = None

# ------------------------------------------------------------------------
# Element data 
# ------------------------------------------------------------------------

ELEMENT_COLOR = {
    "H": (1.0, 1.0, 1.0),
    "C": (0.2, 0.2, 0.2),
    "N": (0.2, 0.3, 1.0),
    "O": (1.0, 0.2, 0.2),
    "S": (1.0, 0.9, 0.2),
}

COV_RAD = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05}

def get_or_make_material(name, color):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs[0].default_value = (*color, 1.0)
    return m

# ------------------------------------------------------------------------
# Preset geometries 
# ------------------------------------------------------------------------

def preset_atoms_bonds(kind):
    """Return (atoms, bonds) tuples for preset molecules."""
    if kind == 'H2O':
        d = 0.9572; ang = math.radians(104.5/2)
        h1 = Vector(( d*sin(ang),  d*cos(ang), 0))
        h2 = Vector((-d*sin(ang),  d*cos(ang), 0))
        atoms = [("O", Vector((0,0,0))), ("H", h1), ("H", h2)]
        bonds = [(0,1),(0,2)]
        return atoms, bonds

    if kind == 'CH4':
        d = 1.09; a = d / math.sqrt(3)
        atoms = [("C", Vector((0,0,0)))]
        offs = [( a,  a,  a), (-a, -a,  a), (-a,  a, -a), ( a, -a, -a)]
        atoms += [("H", Vector(v)) for v in offs]
        bonds = [(0,1),(0,2),(0,3),(0,4)]
        return atoms, bonds

    if kind == 'CO2':
        d = 1.16
        atoms = [("O", Vector((0,0,-d))), ("C", Vector((0,0,0))), ("O", Vector((0,0,d)))]
        bonds = [(0,1),(1,2)]
        return atoms, bonds

    if kind == 'NH3':
        d = 1.01; elev = math.radians(68)
        R = d * math.cos(elev); z = d * math.sin(elev)
        atoms = [("N", Vector((0,0,0)))]
        for k in range(3):
            ang = 2*math.pi*k/3
            atoms.append(("H", Vector((R*math.cos(ang), R*math.sin(ang), z))))
        bonds = [(0,1),(0,2),(0,3)]
        return atoms, bonds

    if kind == 'BENZENE':
        Rc = 1.39; Rh = 1.09
        atoms = []
        for k in range(6):
            th = 2*math.pi*k/6
            atoms.append(("C", Vector((Rc*math.cos(th), Rc*math.sin(th), 0))))
        for k in range(6):
            th = 2*math.pi*k/6
            dirv = Vector((math.cos(th), math.sin(th), 0))
            atoms.append(("H", atoms[k][1] + dirv*Rh))
        bonds = [(i,(i+1)%6) for i in range(6)] + [(i,6+i) for i in range(6)]
        return atoms, bonds

    if kind == 'ETHANOL':
        c1 = Vector((0,0,0)); c2 = Vector((1.54,0,0))
        o = c2 + Vector((1.43,0.5,0))
        atoms = [("C", c1), ("C", c2), ("O", o), ("H", o + Vector((0.8,0.4,0)))]
        for v in [(0.9, 0.9, 0), (0.9, -0.9, 0), (0.9, 0, 0.9)]:
            atoms.append(("H", c1 + Vector(v)))
        for v in [(1.3, 0.9, 0), (1.3, -0.9, 0)]:
            atoms.append(("H", c2 + Vector(v)))
        bonds = [(0,1),(1,2),(2,3),(0,4),(0,5),(0,6),(1,7),(1,8)]
        return atoms, bonds

    if kind == 'ACETIC_ACID':
        c1 = Vector((0,0,0)); c2 = Vector((1.52,0,0))
        o1 = c2 + Vector((1.23,0.0,0.8)); o2 = c2 + Vector((1.23,0.0,-0.8))
        h_o = o2 + Vector((0.6,0.0,-0.6))
        atoms = [("C", c1), ("C", c2), ("O", o1), ("O", o2), ("H", h_o)]
        for v in [(0.9, 0.9, 0), (0.9, -0.9, 0), (0.9, 0, 0.9)]:
            atoms.append(("H", c1 + Vector(v)))
        bonds = [(0,1),(1,2),(1,3),(3,4),(0,5),(0,6),(0,7)]
        return atoms, bonds

    if kind == 'FORMALDEHYDE':
        c = Vector((0,0,0)); o = Vector((1.21,0,0))
        atoms = [("C", c), ("O", o)]
        for v in [(0.9, 0.7, 0), (0.9, -0.7, 0)]:
            atoms.append(("H", c + Vector(v)))
        bonds = [(0,1),(0,2),(0,3)]
        return atoms, bonds

    if kind == 'NaCl':
        atoms = []; bonds = []; spacing = 2.82
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    offset = Vector((i,j,k)) * spacing
                    atoms.append(("Na" if (i+j+k)%2==0 else "Cl", offset))
        for i in range(len(atoms)):
            for j in range(i+1,len(atoms)):
                if (atoms[i][1]-atoms[j][1]).length < spacing*1.01:
                    bonds.append((i,j))
        return atoms, bonds

    if kind == 'GLYCINE':
        c_alpha = Vector((0,0,0))
        n = c_alpha + Vector((-1.35, 0.0, 0.0))
        c_car = c_alpha + Vector((1.52, 0.0, 0.0))
        o1 = c_car + Vector((1.24, 0.7, 0.0))
        o2 = c_car + Vector((1.24, -0.7, 0.0))
        h_n1 = n + Vector((-0.9, 0.5, 0.0))
        h_n2 = n + Vector((-0.9, -0.5, 0.0))
        h_c1 = c_alpha + Vector((0, 0.9, 0.8))
        h_c2 = c_alpha + Vector((0, -0.9, 0.8))
        h_oh = o2 + Vector((0.6, -0.5, 0.0))
        atoms = [
            ("N", n), ("C", c_alpha), ("C", c_car),
            ("O", o1), ("O", o2),
            ("H", h_n1), ("H", h_n2), ("H", h_c1), ("H", h_c2), ("H", h_oh)
        ]
        bonds = [(0,1),(1,2),(2,3),(2,4),(4,9),(0,5),(0,6),(1,7),(1,8)]
        return atoms, bonds
    
    if kind == 'C60':
        from math import sqrt
        phi = (1 + sqrt(5)) / 2  
        coords = [

            (0, 1, 3*phi), (0, -1, 3*phi), (0, 1, -3*phi), (0, -1, -3*phi),
            (1, 3*phi, 0), (-1, 3*phi, 0), (1, -3*phi, 0), (-1, -3*phi, 0),
            (3*phi, 0, 1), (3*phi, 0, -1), (-3*phi, 0, 1), (-3*phi, 0, -1),
            (2, phi, 2*phi), (2, -phi, 2*phi), (-2, phi, 2*phi), (-2, -phi, 2*phi),
            (2, phi, -2*phi), (2, -phi, -2*phi), (-2, phi, -2*phi), (-2, -phi, -2*phi),
            (phi, 2*phi, 2), (-phi, 2*phi, 2), (phi, -2*phi, 2), (-phi, -2*phi, 2),
            (phi, 2*phi, -2), (-phi, 2*phi, -2), (phi, -2*phi, -2), (-phi, -2*phi, -2),
            (2*phi, 2, phi), (-2*phi, 2, phi), (2*phi, -2, phi), (-2*phi, -2, phi),
            (2*phi, 2, -phi), (-2*phi, 2, -phi), (2*phi, -2, -phi), (-2*phi, -2, -phi)
        ]
        atoms = [("C", Vector(v)) for v in coords]
        bonds = []
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                d = (atoms[i][1] - atoms[j][1]).length
                if 3.3 < d < 3.7:  
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'GLUCOSE':
        atoms = [
            ("C", Vector((0.0, 0.0, 0.0))),
            ("C", Vector((1.4, 0.0, 0.0))),
            ("C", Vector((2.0, 1.2, 0.0))),
            ("C", Vector((1.4, 2.4, 0.0))),
            ("C", Vector((0.0, 2.4, 0.0))),
            ("O", Vector((-0.6, 1.2, 0.0))),
            ("O", Vector((0.0, -1.0, 0.0))),
            ("O", Vector((2.4, -0.6, 0.0))),
            ("O", Vector((3.0, 1.8, 0.0))),
            ("O", Vector((2.0, 3.4, 0.0))),
            ("O", Vector((-1.0, 3.0, 0.0))),
            ("H", Vector((0.0, -1.8, 0.0))),
            ("H", Vector((2.4, -1.4, 0.0))),
            ("H", Vector((3.6, 1.8, 0.0))),
            ("H", Vector((2.4, 4.0, 0.0))),
            ("H", Vector((-1.6, 3.0, 0.0))),
            ("H", Vector((0.0, 3.2, 0.9))),
            ("H", Vector((1.4, 3.2, 0.9))),
            ("H", Vector((2.0, 1.2, 0.9))),
            ("H", Vector((1.4, 0.0, 0.9)))
        ]

        bonds = [
            (0,1),(1,2),(2,3),(3,4),(4,5),(5,0),
            (0,6),(1,7),(2,8),(3,9),(4,10),
            (6,11),(7,12),(8,13),(9,14),(10,15),
            (4,16),(3,17),(2,18),(1,19)
        ]
        return atoms, bonds

    if kind == 'CAFFEINE':
        atoms = [
            ("C", Vector((0, 0, 0))),
            ("N", Vector((1.3, 0.0, 0))),
            ("C", Vector((2.3, 1.0, 0))),
            ("N", Vector((3.4, 0.0, 0))),
            ("C", Vector((2.3, -1.0, 0))),
            ("N", Vector((1.3, -2.0, 0))),
            ("C", Vector((0, -2.5, 0))),
            ("O", Vector((-1.2, -2.7, 0))),
            ("N", Vector((0, 1.4, 0))),
            ("C", Vector((1.0, 2.4, 0))),
            ("O", Vector((2.2, 2.6, 0))),
            ("C", Vector((3.7, -2.0, 0))),
            ("N", Vector((4.5, -1.0, 0))),
            ("C", Vector((5.2, 0.0, 0))),
            ("O", Vector((5.7, 1.2, 0))),
            ("H", Vector((-0.8, 0.2, 0))),
            ("H", Vector((0.0, -3.5, 0))),
            ("H", Vector((4.0, -3.0, 0))),
            ("H", Vector((6.0, -0.4, 0))),
        ]
        bonds = [
            (0,1),(1,2),(2,3),(3,4),(4,1),
            (4,5),(5,6),(6,7),(0,8),(8,9),(9,10),
            (3,12),(12,13),(13,14),(13,11),
            (0,15),(6,16),(11,18),(13,19)
        ]
        return atoms, bonds

    if kind == 'ETHYLENE':
        c1 = Vector((0, 0, 0))
        c2 = Vector((1.34, 0, 0))
        atoms = [("C", c1), ("C", c2)]
        h_positions = [(-0.9, 0.9, 0), (-0.9, -0.9, 0), (2.24, 0.9, 0), (2.24, -0.9, 0)]
        atoms += [("H", Vector(h)) for h in h_positions]
        bonds = [(0,1),(0,2),(0,3),(1,4),(1,5)]
        return atoms, bonds

    if kind == 'ADENINE':
        coords = [
            ("N", (0, 0, 0)), ("C", (1.4, 0, 0)), ("N", (2.1, 1.1, 0)), ("C", (1.4, 2.2, 0)),
            ("C", (0, 2.2, 0)), ("N", (-0.7, 1.1, 0)), ("C", (2.8, -0.9, 0)), ("N", (4.0, -0.4, 0)),
            ("C", (3.4, 1.0, 0)), ("N", (4.8, 1.5, 0)), ("H", (-0.9, -0.7, 0)), ("H", (4.5, -1.8, 0)),
            ("H", (5.6, 1.8, 0))
        ]
        atoms = [(e, Vector(v)) for e, v in coords]
        bonds = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(1,6),(6,7),(7,8),(8,2),(8,9),(0,10),(6,11),(9,12)]
        return atoms, bonds
    
    if kind == 'ATP':
        atoms = []
        # Adenine ring
        base, base_bonds = preset_atoms_bonds('ADENINE')
        atoms += [(e, p + Vector((0, 0, 0))) for e, p in base]
        offset = len(atoms)
        bonds = [(i, j) for i, j in base_bonds]

        # Ribose (sugar)
        sugar = [
            ("C", Vector((5.0, 0.5, 0.0))), ("C", Vector((6.3, 0.0, 0.0))),
            ("O", Vector((7.5, 0.5, 0.0))), ("C", Vector((6.3, 1.5, 0.0))),
            ("O", Vector((5.0, 1.8, 0.0))), ("H", Vector((8.0, 0.8, 0.0))),
        ]
        sugar_bonds = [(0,1),(1,2),(2,5),(0,3),(3,4),(4,0)]
        atoms += sugar
        bonds += [(i+offset, j+offset) for i,j in sugar_bonds]

        # Link adenine to sugar
        bonds.append((8, offset))

        # Phosphate tail
        offset2 = len(atoms)
        phosphates = [
            ("P", Vector((8.2, -0.3, 0.0))), ("O", Vector((9.3, -1.0, 0.0))),
            ("O", Vector((8.2, 0.9, 0.0))), ("O", Vector((7.0, -1.0, 0.0))),
            ("P", Vector((10.5, -0.3, 0.0))), ("O", Vector((11.5, -1.0, 0.0))),
            ("O", Vector((10.5, 0.9, 0.0))), ("P", Vector((12.7, -0.3, 0.0))),
            ("O", Vector((13.7, -1.0, 0.0))), ("O", Vector((12.7, 0.9, 0.0))),
        ]
        phosphate_bonds = [
            (0,1),(0,2),(0,3),(0,4),(4,5),(4,6),(4,7),(7,8),(7,9)
        ]
        atoms += phosphates
        bonds += [(i+offset2, j+offset2) for i,j in phosphate_bonds]

        # Link sugar → phosphate
        bonds.append((offset+2, offset2))
        return atoms, bonds

    if kind == 'VITAMIN_C':
        coords = [
            ("C", (0.0, 0.0, 0.0)), ("C", (1.4, 0.0, 0.0)), ("O", (2.2, 1.0, 0.0)),
            ("C", (1.4, 2.0, 0.0)), ("C", (0.0, 2.0, 0.0)), ("O", (-0.8, 1.0, 0.0)),
            ("O", (-1.2, -0.8, 0.0)), ("O", (2.6, -1.0, 0.0)),
            ("H", (-1.8, -1.0, 0.0)), ("H", (3.0, -1.8, 0.0)), ("H", (0.0, 3.0, 0.0)),
            ("H", (1.4, 3.0, 0.0)), ("H", (2.8, 1.0, 0.0))
        ]
        atoms = [(e, Vector(v)) for e, v in coords]
        bonds = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(0,6),(1,7),
                 (6,8),(7,9),(4,10),(3,11),(2,12)]
        return atoms, bonds

    if kind == 'BENZALDEHYDE':
        base_atoms, base_bonds = preset_atoms_bonds('BENZENE')
        atoms = [(e, p.copy()) for e, p in base_atoms]
        bonds = base_bonds.copy()
        # attach CHO group at one carbon
        c_form = atoms[0][1] + Vector((1.4, 0, 0))
        o_form = c_form + Vector((1.2, 0, 0))
        h_form = c_form + Vector((0, 0.8, 0))
        atoms += [("C", c_form), ("O", o_form), ("H", h_form)]
        bonds += [(0, len(atoms)-3), (len(atoms)-3, len(atoms)-2), (len(atoms)-3, len(atoms)-1)]
        return atoms, bonds
    
    if kind == 'ACETONE':
        c1 = Vector((0, 0, 0))
        c2 = Vector((1.52, 0, 0))
        c3 = Vector((3.04, 0, 0))
        o = c2 + Vector((0, 1.2, 0))
        atoms = [("C", c1), ("C", c2), ("C", c3), ("O", o)]
        h_positions = [
            (-0.8, 0.9, 0), (-0.8, -0.9, 0),
            (3.84, 0.9, 0), (3.84, -0.9, 0),
            (1.52, -1.2, 0), (0.0, -1.2, 0)
        ]
        atoms += [("H", Vector(h)) for h in h_positions]
        bonds = [(0,1),(1,2),(1,3),(0,4),(0,5),(2,6),(2,7),(1,8),(0,9)]
        return atoms, bonds

    if kind == 'CHOLESTEROL':
        atoms = []
        bonds = []
        ring_radius = 1.2
        offset = Vector((0, 0, 0))
        # 4 fused rings
        for r in range(4):
            ring = []
            for i in range(6):
                angle = i * math.pi / 3
                ring.append(Vector((math.cos(angle)*ring_radius + r*2.1, math.sin(angle)*ring_radius, 0)))
            start_index = len(atoms)
            atoms += [("C", p + offset) for p in ring]
            for i in range(6):
                bonds.append((start_index+i, start_index+(i+1)%6))
            if r > 0:
                bonds.append((start_index, start_index-2))  # fuse ring
        # attach hydroxyl group
        o = atoms[-1][1] + Vector((0.8, 1.0, 0))
        h = o + Vector((0.6, 0.6, 0))
        atoms += [("O", o), ("H", h)]
        bonds += [(len(atoms)-3, len(atoms)-2), (len(atoms)-2, len(atoms)-1)]
        return atoms, bonds

    if kind == 'UREA':
        c = Vector((0, 0, 0))
        o = Vector((1.2, 0, 0))
        n1 = Vector((-0.9, 0.8, 0))
        n2 = Vector((-0.9, -0.8, 0))
        h_positions = [(n1.x-0.8, n1.y, 0), (n1.x, n1.y+0.8, 0), (n2.x-0.8, n2.y, 0), (n2.x, n2.y-0.8, 0)]
        atoms = [("C", c), ("O", o), ("N", n1), ("N", n2)] + [("H", Vector(h)) for h in h_positions]
        bonds = [(0,1),(0,2),(0,3),(2,4),(2,5),(3,6),(3,7)]
        return atoms, bonds

    if kind == 'PENICILLIN':
        atoms = []
        bonds = []
        # β-lactam ring
        base = [
            ("N", Vector((0, 0, 0))),
            ("C", Vector((1.3, 0, 0))),
            ("C", Vector((1.3, 1.2, 0))),
            ("C", Vector((0, 1.2, 0))),
            ("O", Vector((2.2, -0.6, 0)))
        ]
        bonds += [(0,1),(1,2),(2,3),(3,0),(1,4)]
        atoms += base
        # thiazolidine ring
        offset = len(atoms)
        ring2 = [
            ("S", Vector((-1.3, -0.6, 0))),
            ("C", Vector((-2.3, 0.4, 0))),
            ("C", Vector((-1.5, 1.4, 0))),
            ("C", Vector((-0.3, 1.8, 0))),
        ]
        atoms += ring2
        bonds += [(offset,offset+1),(offset+1,offset+2),(offset+2,offset+3),(offset+3,0),(offset,0)]
        # carboxylic tail
        o1 = Vector((2.0, 2.0, 0))
        o2 = o1 + Vector((0.9, 0.9, 0))
        atoms += [("O", o1), ("O", o2), ("H", o2 + Vector((0.3, 0.8, 0)))]
        bonds += [(2,len(atoms)-3),(len(atoms)-3,len(atoms)-2),(len(atoms)-2,len(atoms)-1)]
        return atoms, bonds

    if kind == 'DOPAMINE':
        ring = []
        for i in range(6):
            angle = i * math.pi / 3
            ring.append(Vector((math.cos(angle)*1.4, math.sin(angle)*1.4, 0)))
        atoms = [("C", p) for p in ring]
        bonds = [(i, (i+1)%6) for i in range(6)]
        # hydroxyls
        o1 = ring[0] + Vector((0, 1.1, 0))
        o2 = ring[1] + Vector((0.9, 0.9, 0))
        atoms += [("O", o1), ("O", o2)]
        bonds += [(0,len(atoms)-2),(1,len(atoms)-1)]
        # side chain
        c_alpha = ring[3] + Vector((1.5, 0, 0))
        c_beta = c_alpha + Vector((1.5, 0, 0))
        n = c_beta + Vector((1.3, 0.8, 0))
        atoms += [("C", c_alpha), ("C", c_beta), ("N", n)]
        bonds += [(3,len(atoms)-3),(len(atoms)-3,len(atoms)-2),(len(atoms)-2,len(atoms)-1)]
        return atoms, bonds

    if kind == 'HEMOGLOBIN':
        atoms = []
        bonds = []
        subunit_centers = [
            Vector((2.5, 0, 0)), Vector((-2.5, 0, 0)),
            Vector((0, 2.5, 0)), Vector((0, -2.5, 0))
        ]
        # Heme-like rings
        for c in subunit_centers:
            ring = []
            for i in range(6):
                angle = i * math.pi / 3
                ring.append(c + Vector((math.cos(angle)*1.0, math.sin(angle)*1.0, 0)))
            start = len(atoms)
            atoms += [("C", p) for p in ring]
            bonds += [(start+i, start+(i+1)%6) for i in range(6)]
            # nitrogen at 4 corners
            for i in (0, 2, 4):
                n = ring[i] + Vector((0, 0, 0.8))
                atoms.append(("N", n))
                bonds.append((start+i, len(atoms)-1))
        # Central Fe atom
        fe = Vector((0, 0, 0))
        atoms.append(("Fe", fe))
        fe_index = len(atoms)-1
        # Link to ring nitrogens
        for i, (el, pos) in enumerate(atoms):
            if el == "N":
                bonds.append((i, fe_index))
        return atoms, bonds

    if kind == 'FULLERENE_C60':
        atoms = []
        bonds = []
        phi = (1 + math.sqrt(5)) / 2  # golden ratio
        a, b = 1.0, 1.0 / phi
        coords = []
        for i in [-1, 1]:
            for j in [-1, 1]:
                for k in [-1, 1]:
                    coords += [
                        (0, i * b, j / a), (i * b, j / a, 0), (i / a, 0, j * b)
                    ]
        # Normalize sphere
        atoms = [("C", Vector(c).normalized() * 2.0) for c in coords]
        # Connect nearby atoms
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < 1.25:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'CHLOROPHYLL':
        atoms = []
        bonds = []
        # Macrocycle
        ring = []
        for i in range(12):
            angle = i * math.pi / 6
            ring.append(Vector((math.cos(angle)*2.0, math.sin(angle)*2.0, 0)))
        atoms += [("C", p) for p in ring]
        bonds += [(i, (i+1)%12) for i in range(12)]
        # Nitrogens
        for i in (0, 3, 6, 9):
            n = ring[i] + Vector((0, 0, 0.8))
            atoms.append(("N", n))
            bonds.append((i, len(atoms)-1))
        # Central Mg
        mg = Vector((0, 0, 0))
        atoms.append(("Mg", mg))
        mg_idx = len(atoms)-1
        for i, (el, pos) in enumerate(atoms):
            if el == "N":
                bonds.append((i, mg_idx))
        # Long tail (phytol)
        start = ring[2]
        prev = start
        for i in range(10):
            c = prev + Vector((1.4, (-1)**i * 0.3, 0))
            atoms.append(("C", c))
            bonds.append((len(atoms)-2 if i else 2, len(atoms)-1))
            prev = c
        return atoms, bonds

    if kind == 'DNA_FRAGMENT':
        atoms = []
        bonds = []
        turns = 4
        steps = 16
        radius = 2.0
        height = 6.0
        for i in range(steps):
            t = i / steps
            angle = t * turns * math.tau
            z = t * height
            # backbone strands
            a = Vector((radius*math.cos(angle), radius*math.sin(angle), z))
            b = Vector((-radius*math.cos(angle), -radius*math.sin(angle), z))
            atoms.append(("P", a))
            atoms.append(("P", b))
            if i > 0:
                bonds.append((2*(i-1), 2*i))
                bonds.append((2*(i-1)+1, 2*i+1))
            # bridges
            mid_a = (a + b) * 0.5
            atoms.append(("N", mid_a))
            bonds.append((2*i, len(atoms)-1))
            bonds.append((2*i+1, len(atoms)-1))
        return atoms, bonds

    if kind == 'GRAPHENE':
        atoms = []
        bonds = []
        n = 8
        a = 1.42
        for i in range(n):
            for j in range(n):
                x = i * 3 * a / 2
                y = math.sqrt(3) * a * (j + 0.5*(i%2))
                atoms.append(("C", Vector((x, y, 0))))
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < a*1.05:
                    bonds.append((i,j))
        return atoms, bonds

    if kind == 'SEROTONIN':
        ring1 = [Vector((math.cos(i*math.pi/3)*1.4, math.sin(i*math.pi/3)*1.4, 0)) for i in range(6)]
        atoms = [("C", v) for v in ring1]
        bonds = [(i,(i+1)%6) for i in range(6)]
        # side chain
        c1 = ring1[2] + Vector((1.3, 0.0, 0))
        c2 = c1 + Vector((1.3, 0.0, 0))
        n = c2 + Vector((1.1, 0.8, 0))
        atoms += [("C", c1), ("C", c2), ("N", n)]
        bonds += [(2,6),(6,7),(7,8)]
        # oxygen group
        o = ring1[5] + Vector((0.8, 1.0, 0))
        atoms += [("O", o)]
        bonds += [(5,len(atoms)-1)]
        return atoms, bonds

    if kind == 'HEMOGLOBIN':
        atoms = []
        bonds = []
        ring_r = 1.2
        centers = [Vector((3*math.cos(i*math.pi/2), 3*math.sin(i*math.pi/2), 0)) for i in range(4)]
        for c in centers:
            ring = [("C", c + Vector((ring_r*math.cos(j*math.pi/2), ring_r*math.sin(j*math.pi/2), 0))) for j in range(4)]
            idx0 = len(atoms)
            atoms += ring
            bonds += [(idx0+j, idx0+(j+1)%4) for j in range(4)]
        fe = Vector((0,0,0))
        atoms.append(("Fe", fe))
        for i in range(0, len(atoms)-1, 4):
            bonds.append((len(atoms)-1, i))
        return atoms, bonds

    if kind == 'ALPHA_HELIX':
        atoms = []
        bonds = []
        turns = 4
        residues_per_turn = 6
        step_angle = 2*math.pi / residues_per_turn
        pitch = 1.5
        radius = 1.2
        total = turns * residues_per_turn
        for i in range(total):
            ang = i * step_angle
            z = i * pitch / residues_per_turn
            c = Vector((radius*math.cos(ang), radius*math.sin(ang), z))
            o = c + Vector((0.5*math.cos(ang+math.pi/2), 0.5*math.sin(ang+math.pi/2), 0))
            n = c - Vector((0.5*math.cos(ang+math.pi/2), 0.5*math.sin(ang+math.pi/2), 0))
            atoms += [("C", c), ("O", o), ("N", n)]
            if i > 0:
                bonds.append((3*i, 3*(i-1)))  # backbone
        return atoms, bonds

    if kind == 'DIAMOND':
        atoms = []
        bonds = []
        a = 1.54  # bond length (Å)
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    offset = Vector((i, j, k)) * a
                    atoms.append(("C", offset))
                    # tetrahedral neighbors
                    if i < 2 and j < 2 and k < 2:
                        atoms.append(("C", offset + Vector((a/4, a/4, a/4))))
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < a*0.9:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'SALT_CRYSTAL':
        atoms = []
        bonds = []
        size = 3
        spacing = 2.8
        for i in range(size):
            for j in range(size):
                for k in range(size):
                    is_na = (i + j + k) % 2 == 0
                    el = "Na" if is_na else "Cl"
                    atoms.append((el, Vector((i, j, k)) * spacing))
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1]-atoms[j][1]).length < spacing*1.1:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'BETA_CAROTENE':
        atoms = []
        bonds = []
        length = 20
        spacing = 1.4
        for i in range(length):
            atoms.append(("C", Vector((i*spacing, 0, 0))))
            if i > 0:
                bonds.append((i-1, i))
            if i % 4 == 0:
                atoms.append(("C", Vector((i*spacing, 1.2, 0))))
                bonds.append((i, len(atoms)-1))
        # terminal rings
        for side in [-1, 1]:
            center = Vector((side*(length-1)*spacing/2, 0, 0))
            for i in range(6):
                th = i * math.pi / 3
                atoms.append(("C", center + Vector((math.cos(th), math.sin(th), 0))*1.2))
        for i in range(len(atoms)-12, len(atoms)):
            bonds.append((len(atoms)-12, i))
        return atoms, bonds

    if kind == 'RETINOL':
        atoms = []
        bonds = []
        for i in range(8):
            atoms.append(("C", Vector((i*1.4, 0, 0))))
            if i > 0:
                bonds.append((i-1, i))
            if i % 2 == 0:
                atoms.append(("C", Vector((i*1.4, 1.1, 0))))
                bonds.append((i, len(atoms)-1))
        atoms.append(("O", Vector((11.2, 0.5, 0))))
        bonds.append((7, len(atoms)-1))
        return atoms, bonds

    if kind == 'IRON_PORPHYRIN':
        atoms = []
        bonds = []
        r = 1.5
        for i in range(8):
            th = i * math.pi / 4
            el = "C" if i % 2 == 0 else "N"
            atoms.append((el, Vector((r*math.cos(th), r*math.sin(th), 0))))
        bonds += [(i, (i+1)%8) for i in range(8)]
        fe = Vector((0,0,0))
        atoms.append(("Fe", fe))
        for i in range(1,9,2):  # bind Fe to N only
            bonds.append((len(atoms)-1, i))
        return atoms, bonds

    if kind == 'COPPER_SULFATE':
        cu = Vector((0,0,0))
        s = Vector((2.0, 0, 0))
        o_positions = [
            s + Vector((1.1, 0, 0)),
            s + Vector((-1.1, 0, 0)),
            s + Vector((0, 1.1, 0)),
            s + Vector((0, -1.1, 0)),
        ]
        water_mols = [Vector((2.5, i*1.0, 0)) for i in range(5)]
        atoms = [("Cu", cu), ("S", s)] + [("O", o) for o in o_positions]
        atoms += [("O", w) for w in water_mols]
        atoms += [("H", w + Vector((0.6, 0.6, 0))) for w in water_mols]
        atoms += [("H", w + Vector((-0.6, 0.6, 0))) for w in water_mols]
        bonds = [(0,1)] + [(1,i) for i in range(2,6)]
        for i in range(5):
            base = 6 + i
            bonds += [(base, base+5), (base, base+10)]
        return atoms, bonds

    if kind == 'ADENINE':
        ring = [Vector((math.cos(i*math.pi/3)*1.4, math.sin(i*math.pi/3)*1.4, 0)) for i in range(6)]
        atoms = [("C", v) for v in ring]
        bonds = [(i,(i+1)%6) for i in range(6)]
        n1 = ring[0] + Vector((1.1, 0.6, 0))
        n2 = ring[2] + Vector((-1.1, -0.6, 0))
        n3 = ring[4] + Vector((0, -1.1, 0))
        atoms += [("N", n1), ("N", n2), ("N", n3)]
        bonds += [(0,6),(2,7),(4,8)]
        return atoms, bonds

    if kind == 'GUANINE':
        ring = [Vector((math.cos(i*math.pi/3)*1.3, math.sin(i*math.pi/3)*1.3, 0)) for i in range(6)]
        atoms = [("C", v) for v in ring]
        bonds = [(i,(i+1)%6) for i in range(6)]
        n1 = ring[1] + Vector((1.0, 0.7, 0))
        n2 = ring[3] + Vector((-1.1, -0.6, 0))
        o = ring[4] + Vector((0, 1.1, 0))
        atoms += [("N", n1), ("N", n2), ("O", o)]
        bonds += [(1,6),(3,7),(4,8)]
        return atoms, bonds
       
    if kind == 'DIAMOND_3D':
        atoms = []
        bonds = []
        size = 4
        a = 1.54  # lattice constant

        for x in range(size):
            for y in range(size):
                for z in range(size):
                    base = Vector((x, y, z)) * a
                    atoms.append(("C", base))
                    atoms.append(("C", base + Vector((a/4, a/4, a/4))))
        # bonds: connect close atoms
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < a * 0.9:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'CARBON_NANOTUBE':
        atoms = []
        bonds = []
        rings = 20
        segments = 12
        r = 3.0
        h_step = 0.5
        a = 1.4

        for i in range(rings):
            z = i * h_step
            for j in range(segments):
                ang = 2 * math.pi * j / segments
                offset = (i % 2) * (math.pi / segments)
                pos = Vector((r * math.cos(ang + offset), r * math.sin(ang + offset), z))
                atoms.append(("C", pos))

        for i in range(rings):
            for j in range(segments):
                idx = i * segments + j
                next_idx = i * segments + ((j + 1) % segments)
                bonds.append((idx, next_idx))
                if i < rings - 1:
                    bonds.append((idx, (i + 1) * segments + j))
        return atoms, bonds

    if kind == 'BCC_LATTICE':
        atoms = []
        bonds = []
        size = 4
        spacing = 2.5
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    base = Vector((x, y, z)) * spacing
                    atoms.append(("Fe", base))
                    atoms.append(("Fe", base + Vector((spacing/2, spacing/2, spacing/2))))
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < spacing * 0.9:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'FCC_LATTICE':
        atoms = []
        bonds = []
        size = 3
        a = 2.5
        offsets = [
            Vector((0,0,0)),
            Vector((0.5,0.5,0)),
            Vector((0.5,0,0.5)),
            Vector((0,0.5,0.5))
        ]
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    for o in offsets:
                        atoms.append(("Al", (Vector((x, y, z)) + o) * a))
        for i in range(len(atoms)):
            for j in range(i+1, len(atoms)):
                if (atoms[i][1] - atoms[j][1]).length < a * 0.8:
                    bonds.append((i, j))
        return atoms, bonds

    if kind == 'CARBON_CAGE':
        atoms = []
        bonds = []
        rings = 8
        segs = 12
        r = 4.0

        for i in range(rings):
            theta = math.pi * i / (rings - 1)
            for j in range(segs):
                phi = 2 * math.pi * j / segs
                pos = Vector((
                    r * math.sin(theta) * math.cos(phi),
                    r * math.sin(theta) * math.sin(phi),
                    r * math.cos(theta)
                ))
                atoms.append(("C", pos))

        for i in range(rings):
            for j in range(segs):
                a = i * segs + j
                b = i * segs + (j + 1) % segs
                if i < rings - 1:
                    c = (i + 1) * segs + j
                    bonds.append((a, c))
                bonds.append((a, b))
        return atoms, bonds

    if kind == 'QUARTZ_LATTICE':
        atoms = []
        bonds = []
        size = 3
        step = 2.7
        for i in range(size):
            for j in range(size):
                for k in range(size):
                    si = Vector((i, j, k)) * step
                    atoms.append(("Si", si))
                    for dx, dy, dz in [(0.5, 0.5, 0), (0.5, 0, 0.5), (0, 0.5, 0.5)]:
                        o = si + Vector((dx, dy, dz)) * step
                        atoms.append(("O", o))
                        bonds.append((len(atoms)-2, len(atoms)-1))
        return atoms, bonds

    if kind == 'PROTEIN_TUBE':
        atoms = []
        bonds = []
        turns = 10
        ring_atoms = 8
        radius = 3.5
        height = 8
        for i in range(turns * ring_atoms):
            t = i * 2 * math.pi / ring_atoms
            z = i * height / (turns * ring_atoms)
            x = radius * math.cos(t)
            y = radius * math.sin(t)
            atoms.append(("C", Vector((x, y, z))))
            if i > 0:
                bonds.append((i-1, i))
            if i % ring_atoms == 0 and i > 0:
                bonds.append((i-ring_atoms, i))
        return atoms, bonds



    return [], []

# ------------------------------------------------------------------------
# Mesh builders (atoms/bonds)
# ------------------------------------------------------------------------

def add_uv_sphere(radius, segments=24, rings=16, location=(0,0,0)):
    mesh = bpy.data.meshes.new("AtomSphere")
    bm = bmesh.new()
    subdiv = max(1, min(6, segments // 8))
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new("Atom", mesh)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    return obj

def _orient_between_vectors(z_from, z_to):
    v = z_from.cross(z_to)
    s = v.length
    c = z_from.dot(z_to)
    if s < 1e-8:
        if c > 0: return Matrix.Identity(4)
        return Matrix.Rotation(math.pi, 4, Vector((1,0,0)))
    vx = Matrix([[0,-v.z,v.y],[v.z,0,-v.x],[-v.y,v.x,0]])
    R3 = Matrix.Identity(3) + vx + (vx @ vx) * ((1 - c) / (s**2))
    M = Matrix.Identity(4)
    M[0][0], M[0][1], M[0][2] = R3[0][0], R3[0][1], R3[0][2]
    M[1][0], M[1][1], M[1][2] = R3[1][0], R3[1][1], R3[1][2]
    M[2][0], M[2][1], M[2][2] = R3[2][0], R3[2][1], R3[2][2]
    return M

def add_cylinder(radius, p0, p1, segments=24):
    axis = p1 - p0
    length = max(axis.length, 1e-8)
    mesh = bpy.data.meshes.new("BondCylinder")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=length
    )
    mat = _orient_between_vectors(Vector((0, 0, 1)), axis.normalized())
    for v in bm.verts:
        v.co = mat @ v.co
        v.co += (p0 + p1) * 0.5
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new("Bond", mesh)
    bpy.context.collection.objects.link(obj)
    return obj

# ------------------------------------------------------------------------
# Assembly
# ------------------------------------------------------------------------

def assign_materials_join(objs, element_tags):
    mat_cache = {}
    def mat_for(el):
        if el not in mat_cache:
            col = ELEMENT_COLOR.get(el, (0.7,0.7,0.7))
            mat_cache[el] = get_or_make_material(f"EL_{el}", col)
        return mat_cache[el]
    mat_bond = get_or_make_material("EL_BOND", (0.6,0.6,0.6))

    for obj, tag in zip(objs, element_tags):
        obj.data.materials.clear()
        if tag == "__BOND__":
            obj.data.materials.append(mat_bond)
        else:
            obj.data.materials.append(mat_for(tag))

    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active

def make_molecule_mesh(props, atoms, bonds):
    objs, tags = [], []

    scale = props.scale
    atom_r_scale = props.atom_radius
    bond_r = props.bond_radius
    seg_sph = props.sphere_segments
    seg_cyl = props.bond_segments

    for el, p in atoms:
        r_cov = COV_RAD.get(el, 0.75) * atom_r_scale * scale
        o = add_uv_sphere(radius=r_cov, segments=seg_sph, rings=max(8, seg_sph//2), location=(p*scale))
        objs.append(o); tags.append(el)

    for i, j in bonds:
        if i >= len(atoms) or j >= len(atoms):
            print(f"[WARN] Invalid bond index ({i}, {j}) for {len(atoms)} atoms.")
            continue
        p0 = atoms[i][1] * scale
        p1 = atoms[j][1] * scale
        o = add_cylinder(radius=bond_r * scale, p0=p0, p1=p1, segments=seg_cyl)
        objs.append(o)
        tags.append("__BOND__")

    if not objs:
        return None

    joined = assign_materials_join(objs, tags)
    if props.smooth_shading:
        bpy.ops.object.shade_smooth()
    joined.name = "Molecule"
    return joined

# ------------------------------------------------------------------------
# Generate / Rebuild
# ------------------------------------------------------------------------

def build_from_props(props):
    atoms, bonds = preset_atoms_bonds(props.preset)
    if not atoms:
        print("[Molecule Generator] Empty preset.")
        return None
    return make_molecule_mesh(props, atoms, bonds)

def rebuild_molecule(obj, props):
    new_obj = build_from_props(props)
    if not new_obj:
        return obj
    new_data = new_obj.data.copy()
    old_data = obj.data
    obj.data = new_data
    obj.name = obj.data.name = "Molecule"
    bpy.data.objects.remove(new_obj, do_unlink=True)
    if old_data and old_data.users == 0:
        bpy.data.meshes.remove(old_data)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def generate_molecule(context):
    p = context.scene.molgen_props
    obj = context.active_object

    if obj and obj.type == "MESH" and obj.get("molecule_generator") and obj.select_get():
        rebuild_molecule(obj, p)
        return obj

    new_obj = build_from_props(p)
    if not new_obj:
        return None
    new_obj["molecule_generator"] = True
    context.view_layer.objects.active = new_obj
    new_obj.select_set(True)
    return new_obj

# ------------------------------------------------------------------------
# Live Update
# ------------------------------------------------------------------------

def update_molecule(self, context):
    if not self.live_update:
        return
    obj = context.active_object
    if (
        not obj
        or obj.type != "MESH"
        or "molecule_generator" not in obj
        or not obj.select_get()
    ):
        return
    rebuild_molecule(obj, self)

# ------------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------------

class MoleculeGenProperties(bpy.types.PropertyGroup):
    live_update: bpy.props.BoolProperty(name="Live Update", default=False)

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=[
            ('H2O', "H2O (Water)", ""),
            ('CH4', "CH4 (Methane)", ""),
            ('CO2', "CO2 (Carbon Dioxide)", ""),
            ('NH3', "NH3 (Ammonia)", ""),
            ('BENZENE', "C6H6 (Benzene)", ""),
            ('ETHANOL', "C₂H₅OH (Ethanol)", ""),
            ('ACETIC_ACID', "CH₃COOH (Acetic Acid)", ""),
            ('FORMALDEHYDE', "CH₂O (Formaldehyde)", ""),
            ('NaCl', "NaCl (Sodium Chloride)", ""),
            ('GLYCINE', "C₂H₅NO₂ (Glycine)", ""),
            ('C60', "C₆₀ (Buckminsterfullerene)", ""),
            ('GLUCOSE', "C₆H₁₂O₆ (Glucose)", ""),
            ('CAFFEINE', "C₈H₁₀N₄O₂ (Caffeine)", ""),
            ('ETHYLENE', "C₂H₄ (Ethylene)", ""),
            ('ADENINE', "C₅H₅N₅ (Adenine)", ""),
            ('ATP', "C₁₀H₁₆N₅O₁₃P₃ (ATP)", ""),
            ('VITAMIN_C', "C₆H₈O₆ (Vitamin C)", ""),
            ('BENZALDEHYDE', "C₆H₅CHO (Benzaldehyde)", ""),
            ('ACETONE', "C₃H₆O (Acetone)", ""),
            ('CHOLESTEROL', "C₂₇H₄₆O (Cholesterol, simplified)", ""),
            ('UREA', "CH₄N₂O (Urea)", ""),
            ('PENICILLIN', "C₁₆H₁₈N₂O₄S (Penicillin, simplified)", ""),
            ('DOPAMINE', "C₈H₁₁NO₂ (Dopamine)", ""),
            ('FULLERENE_C60', "C₆₀ (Fullerene / Buckyball)", ""),
            ('DNA_FRAGMENT', "DNA Double Helix Fragment", ""),
            ('GRAPHENE', "Graphene Sheet", ""),
            ('SEROTONIN', "C₁₀H₁₂N₂O (Serotonin)", ""),
            ('HEMOGLOBIN', "Hemoglobin (Simplified)", ""),
            ('ALPHA_HELIX', "Protein Alpha Helix", ""),
            ('CHLOROPHYLL', "C₅₅H₇₂MgN₄O₅ (Chlorophyll)", ""),
            ('DIAMOND', "C (Diamond lattice)", ""),
            ('SALT_CRYSTAL', "NaCl Crystal (3D lattice)", ""),
            ('BETA_CAROTENE', "C₄₀H₅₆ (Beta-Carotene)", ""),
            ('RETINOL', "C₂₀H₃₀O (Vitamin A / Retinol)", ""),
            ('IRON_PORPHYRIN', "C₂₀H₁₂FeN₄ (Iron Porphyrin)", ""),
            ('COPPER_SULFATE', "CuSO₄·5H₂O (Copper Sulfate)", ""),
            ('ADENINE', "C₅H₅N₅ (Adenine)", ""),
            ('GUANINE', "C₅H₅N₅O (Guanine)", ""),
            ('DIAMOND_3D', "C (Diamond Lattice 3D)", ""),
            ('CARBON_NANOTUBE', "Carbon Nanotube", ""),
            ('BCC_LATTICE', "Fe (BCC Lattice)", ""),
            ('FCC_LATTICE', "Al (FCC Lattice)", ""),
            ('CARBON_CAGE', "Carbon Cage (Spherical)", ""),
            ('QUARTZ_LATTICE', "SiO₂ (Quartz Lattice)", ""),
            ('PROTEIN_TUBE', "Protein Nanotube", ""),
            
        ],
        default='H2O',
        update=update_molecule
    )

    scale: bpy.props.FloatProperty(name="Global Scale", default=1.0, min=0.01, max=10.0, subtype='FACTOR', update=update_molecule)
    atom_radius: bpy.props.FloatProperty(name="Atom Radius Scale", default=0.35, min=0.05, max=2.0, subtype='FACTOR', update=update_molecule)
    bond_radius: bpy.props.FloatProperty(name="Bond Radius", default=0.06, min=0.005, max=1.0, subtype='FACTOR', update=update_molecule)

    sphere_segments: bpy.props.IntProperty(name="Atom Segments", default=24, min=8, max=64, subtype='FACTOR', update=update_molecule)
    bond_segments: bpy.props.IntProperty(name="Bond Segments", default=24, min=8, max=64, subtype='FACTOR', update=update_molecule)

    smooth_shading: bpy.props.BoolProperty(name="Smooth Shading", default=True, update=update_molecule)

class MOLGEN_OT_generate(bpy.types.Operator):
    bl_idname = "molecule.generate"
    bl_label = "Generate Molecule"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        generate_molecule(context)
        return {"FINISHED"}
    
# ------------------------------------------------------------------------
# UI
# ------------------------------------------------------------------------

class VIEW3D_PT_molecule_generator(bpy.types.Panel):
    bl_label = "Molecule"
    bl_idname = "VIEW3D_PT_molecule_generator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Molecule" 

    def draw(self, context):
        if relay_updater:
            relay_updater.draw(self.layout)
        layout = self.layout
        p = context.scene.molgen_props
        o = context.object

        layout.operator("molecule.generate", text="Generate Molecule", icon="PARTICLE_DATA")
        layout.prop(p, "live_update", toggle=True)

        layout.separator(factor=0.5)

        layout.prop(p, "preset")

        layout.separator(factor=0.5)

        layout.prop(p, "scale")
        layout.prop(p, "atom_radius")
        layout.prop(p, "bond_radius")

        layout.separator(factor=0.5)

        layout.prop(p, "sphere_segments")
        layout.prop(p, "bond_segments")

        layout.prop(p, "smooth_shading", toggle=True)

        layout.separator(factor=0.5)

        if (
            o
            and o.type == "MESH"
            and "molecule_generator" in o
            and o.select_get()
        ):
            layout.label(text=f"Editing: {o.name}", icon="PARTICLE_DATA")
        else:
            layout.label(text="No molecule selected", icon="INFO")

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    MoleculeGenProperties,
    MOLGEN_OT_generate,
    VIEW3D_PT_molecule_generator,
)

def register():
    if relay_updater:
        relay_updater.register("blender-molecule")
    for c in classes:
        try:
            bpy.utils.register_class(c)
        except Exception:
            pass
    bpy.types.Scene.molgen_props = bpy.props.PointerProperty(type=MoleculeGenProperties)

def unregister():
    if relay_updater:
        relay_updater.unregister()
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "molgen_props"):
        del bpy.types.Scene.molgen_props

if __name__ == "__main__":
    register()
