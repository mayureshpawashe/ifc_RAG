import ifcopenshell
import pandas as pd

# === Configuration ===
IFC_FILE = "ES25_BYGGOFFICE_KALK.ifc"  # Change to your IFC filename
EXPORT_FILE = "ifc_slab_detailed_export.xlsx"

# === Open IFC ===
ifc = ifcopenshell.open(IFC_FILE)

# === Global unit mapping
unit_map = {}
for unit in ifc.by_type("IfcUnitAssignment")[0].Units:
    if hasattr(unit, "UnitType"):
        unit_map[unit.UnitType] = getattr(unit, "Name", unit.is_a())

quantity_unit_lookup = {
    "IfcQuantityLength": "LENGTHUNIT",
    "IfcQuantityArea": "AREAUNIT",
    "IfcQuantityVolume": "VOLUMEUNIT",
    "IfcQuantityCount": "COUNTUNIT"
}

# === Target Psets and Qsets ===
target_psets = {
    "AC_Pset_RenovationAndPhasing",
    "Pset_SlabCommon",
    "Pset_FireRatingProperties"
}
target_qsets = {"ArchiCADQuantities"}

records = []

for slab in ifc.by_type("IfcSlab"):
    base = {
        "GlobalId": slab.GlobalId,
        "Name": slab.Name or "",
        "Tag": getattr(slab, "Tag", ""),
        "ObjectType": getattr(slab, "ObjectType", ""),
        "PredefinedType": getattr(slab, "PredefinedType", "")
    }

    # === Location info
    storey = ""
    top_elev = bottom_elev = global_top = global_bottom = None
    for rel in getattr(slab, "ContainedInStructure", []):
        if rel.is_a("IfcRelContainedInSpatialStructure"):
            struct = rel.RelatingStructure
            if struct and struct.is_a("IfcBuildingStorey"):
                storey = struct.Name
                top_elev = getattr(struct, "Elevation", None)
                global_top = top_elev
                global_bottom = top_elev
    base["Location.Storey"] = storey
    base["Location.Top Elevation"] = top_elev
    base["Location.Bottom Elevation"] = bottom_elev
    base["Location.Global Top Elevation"] = global_top
    base["Location.Global Bottom Elevation"] = global_bottom

    # === Geometry info
    bbox_len = bbox_wid = bbox_hei = gx = gy = gz = None
    shape = getattr(slab, "Representation", None)
    if shape and hasattr(shape, "Representations"):
        for rep in shape.Representations:
            if hasattr(rep, "Items"):
                for item in rep.Items:
                    if item.is_a("IfcBoundingBox"):
                        bbox_len = item.XDim
                        bbox_wid = item.YDim
                        bbox_hei = item.ZDim
                        coords = getattr(item.Location, "Coordinates", [])
                        gx, gy, gz = (coords + [None]*3)[:3]
                        break
    base["Geometry.Bounding Box Length"] = bbox_len
    base["Geometry.Bounding Box Width"] = bbox_wid
    base["Geometry.Bounding Box Height"] = bbox_hei
    base["Geometry.Global X"] = gx
    base["Geometry.Global Y"] = gy
    base["Geometry.Global Z"] = gz

    # === Membership info
    group_names = []
    for rel in getattr(slab, "HasAssignments", []):
        if rel.is_a("IfcRelAssignsToGroup") and hasattr(rel, "RelatingGroup"):
            group = rel.RelatingGroup
            if hasattr(group, "Name"):
                group_names.append(group.Name)
    base["Membership.Layer"] = "; ".join(group_names)

    # === Property & Quantity sets
    for rel in getattr(slab, "IsDefinedBy", []):
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pdef = rel.RelatingPropertyDefinition
        set_name = getattr(pdef, "Name", "")

        # --- Property Set
        if pdef.is_a("IfcPropertySet") and set_name in target_psets:
            for prop in pdef.HasProperties:
                if prop.is_a("IfcPropertySingleValue"):
                    val = getattr(prop.NominalValue, "wrappedValue", None)
                    unit = getattr(prop, "Unit", None)
                    unit_name = getattr(unit, "Name", None)
                    record = base.copy()
                    record.update({
                        "Data Type": "Property",
                        "Set Name": set_name,
                        "Attribute Name": prop.Name,
                        "Value": val,
                        "Unit": unit_name
                    })
                    records.append(record)

        # --- Quantity Set
        elif pdef.is_a("IfcElementQuantity") and set_name in target_qsets:
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
                                "Set Name": set_name,
                                "Attribute Name": qty.Name,
                                "Value": value,
                                "Unit": global_unit
                            })
                            records.append(record)

# === Export to Excel
df = pd.DataFrame(records)
df.to_excel(EXPORT_FILE, index=False)

print(f"✅ Exported: {EXPORT_FILE} with {len(df)} rows")
