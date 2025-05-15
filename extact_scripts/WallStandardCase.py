import ifcopenshell
import pandas as pd

# === Config
IFC_FILE = "ES25_BYGGOFFICE_KALK.ifc"
EXPORT_FILE = "ifc_wallstandardcase_full_export.xlsx"

# === Open IFC file
ifc = ifcopenshell.open(IFC_FILE)

# === Global unit mapping
unit_map = {}
unit_assignments = ifc.by_type("IfcUnitAssignment")
if unit_assignments:
    for unit in unit_assignments[0].Units:
        if hasattr(unit, "UnitType"):
            unit_map[unit.UnitType] = getattr(unit, "Name", unit.is_a())

# === Quantity type to unit type
quantity_unit_lookup = {
    "IfcQuantityLength": "LENGTHUNIT",
    "IfcQuantityArea": "AREAUNIT",
    "IfcQuantityVolume": "VOLUMEUNIT",
    "IfcQuantityCount": "COUNTUNIT"
}

# === Property sets to include
target_psets = {
    "Pset_WallCommon",
    "Pset_FireRatingProperties",
    "AC_Pset_RenovationAndPhasing"
}

# === Quantity sets to include
target_qsets = {"ArchiCADQuantities"}

records = []

for wall in ifc.by_type("IfcWallStandardCase"):
    base = {
        "GlobalId": wall.GlobalId,
        "Name": wall.Name or "",
        "Tag": getattr(wall, "Tag", ""),
        "ObjectType": getattr(wall, "ObjectType", ""),
        "IfcEntity": wall.is_a()
    }

    for rel in getattr(wall, "IsDefinedBy", []):
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue

        pdef = rel.RelatingPropertyDefinition
        pset_name = getattr(pdef, "Name", "")

        # === Properties
        if pdef.is_a("IfcPropertySet") and pset_name in target_psets:
            for prop in pdef.HasProperties:
                if prop.is_a("IfcPropertySingleValue"):
                    val = getattr(prop.NominalValue, "wrappedValue", None)
                    unit = getattr(prop, "Unit", None)
                    unit_name = getattr(unit, "Name", None)
                    record = base.copy()
                    record.update({
                        "Data Type": "Property",
                        "Set Name": pset_name,
                        "Attribute Name": prop.Name,
                        "Value": val,
                        "Unit": unit_name
                    })
                    records.append(record)

        # === Quantities
        elif pdef.is_a("IfcElementQuantity") and pset_name in target_qsets:
            for qty in pdef.Quantities:
                for attr in dir(qty):
                    if attr.endswith("Value"):
                        value = getattr(qty, attr)
                        if value is not None:
                            q_type = qty.is_a()
                            unit_type = quantity_unit_lookup.get(q_type)
                            global_unit = unit_map.get(unit_type, "")
                            record = base.copy()
                            record.update({
                                "Data Type": "Quantity",
                                "Set Name": pset_name,
                                "Attribute Name": qty.Name,
                                "Value": value,
                                "Unit": global_unit
                            })
                            records.append(record)

# === Export
df = pd.DataFrame(records)
df.to_excel(EXPORT_FILE, index=False)
print(f"✅ Exported full IfcWallStandardCase data to: {EXPORT_FILE}")
