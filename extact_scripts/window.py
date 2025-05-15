import ifcopenshell
import pandas as pd

# === Load IFC ===
IFC_FILE = "ES25_BYGGOFFICE_KALK.ifc"
EXPORT_FILE = "ifc_windows_export.xlsx"
ifc = ifcopenshell.open(IFC_FILE)

# === Get global unit mapping (e.g. IfcAreaUnit → m2)
unit_map = {}
unit_assignments = ifc.by_type("IfcUnitAssignment")
if unit_assignments:
    for unit in unit_assignments[0].Units:
        unit_type = unit.is_a()
        unit_name = getattr(unit, "Name", None)
        if hasattr(unit, "UnitType"):
            unit_map[unit.UnitType] = unit_name or unit_type

# === Set filters
target_qtypes = {
    "IfcQuantityLength": "LENGTHUNIT",
    "IfcQuantityArea": "AREAUNIT",
    "IfcQuantityVolume": "VOLUMEUNIT",
    "IfcQuantityCount": "COUNTUNIT"
}

records = []

for win in ifc.by_type("IfcWindow"):
    guid = win.GlobalId
    name = win.Name or ""
    obj_type = getattr(win, "ObjectType", "")
    storey = ""
    for rel in getattr(win, "ContainedInStructure", []):
        if rel.is_a("IfcRelContainedInSpatialStructure"):
            parent = rel.RelatingStructure
            if parent and parent.is_a("IfcBuildingStorey"):
                storey = parent.Name

    material = ""
    for rel in getattr(win, "HasAssociations", []):
        if rel.is_a("IfcRelAssociatesMaterial"):
            mat = rel.RelatingMaterial

            # Case 1: Direct material
            if hasattr(mat, "Name"):
                material = mat.Name

            # Case 2: Layered material
            elif hasattr(mat, "ForLayerSet"):
                layers = getattr(mat.ForLayerSet, "MaterialLayers", [])
                if layers and hasattr(layers[0], "Material"):
                    material = layers[0].Material.Name

            # Case 3: MaterialProfileSet (rare)
            elif hasattr(mat, "MaterialProfiles"):
                profiles = getattr(mat, "MaterialProfiles", [])
                if profiles and hasattr(profiles[0], "Material"):
                    material = profiles[0].Material.Name

    for rel in getattr(win, "IsDefinedBy", []):
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pdef = rel.RelatingPropertyDefinition

        # Quantities with correct unit fallback
        if pdef.is_a("IfcElementQuantity"):
            for qty in pdef.Quantities:
                for attr in dir(qty):
                    if attr.endswith("Value"):
                        val = getattr(qty, attr)
                        if val is not None:
                            qty_type = qty.is_a()
                            unit_type = target_qtypes.get(qty_type, "")
                            global_unit = unit_map.get(unit_type, "")
                            records.append({
                                "GUID": guid,
                                "Element Type": "IfcWindow",
                                "Name": name,
                                "ObjectType": obj_type,
                                "Storey": storey,
                                "Material": material,
                                "Data Type": "Quantity",
                                "Set Name": pdef.Name,
                                "Attribute Name": qty.Name,
                                "Value": val,
                                "Unit": global_unit
                            })

# === Export
df = pd.DataFrame(records)
df.to_excel(EXPORT_FILE, index=False)
print(f"✅ Exported window quantities with correct global units to: {EXPORT_FILE}")
