import ifcopenshell
import pandas as pd

# === Configuration ===
IFC_FILE = "ES25_BYGGOFFICE_KALK.ifc"
EXPORT_FILE = "ifc_wall_enriched_export.xlsx"

# === Load IFC File ===
ifc_file = ifcopenshell.open(IFC_FILE)
records = []

# === Target Property and Quantity Names ===
target_psets = {
    "Pset_WallCommon", "Pset_FireRatingProperties", "MMI",
    "AC_Pset_RenovationAndPhasing"
}
target_properties = {
    "IsExternal", "LoadBearing", "FireRating", "Renovation Status",
    "MMI", "MMI dato", "MMI signatur"
}
target_qsets = {"BaseQuantities", "ArchiCADQuantities"}
target_quantities = {
    "Length", "Width", "Height", "Volume", "GrossArea", "NetArea", 
    "GrossVolume", "NetVolume", "GrossFootprintArea", 
    "NetFootprintArea", "GrossSideArea", "NetSideArea", "Perimeter"
}

# === Extract Data ===
for wall in ifc_file.by_type("IfcWall"):
    guid = wall.GlobalId
    name = wall.Name or ""
    obj_type = getattr(wall, "ObjectType", "")
    
    # === Get Storey ===
    storey = ""
    for rel in getattr(wall, "ContainedInStructure", []):
        if rel.is_a("IfcRelContainedInSpatialStructure"):
            parent = rel.RelatingStructure
            if parent and parent.is_a("IfcBuildingStorey"):
                storey = parent.Name

    # === Get Material ===
    material = ""
    for rel in getattr(wall, "HasAssociations", []):
        if rel.is_a("IfcRelAssociatesMaterial"):
            mat = rel.RelatingMaterial
            if hasattr(mat, "Name"):
                material = mat.Name
            elif hasattr(mat, "ForLayerSet") and mat.ForLayerSet.MaterialLayers:
                material = mat.ForLayerSet.MaterialLayers[0].Material.Name

    # === Look for Properties and Quantities ===
    for rel in getattr(wall, "IsDefinedBy", []):
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue

        prop_def = rel.RelatingPropertyDefinition

        # --- Property Sets ---
        if prop_def.is_a("IfcPropertySet") and prop_def.Name in target_psets:
            for prop in prop_def.HasProperties:
                if prop.is_a("IfcPropertySingleValue") and prop.Name in target_properties:
                    val = getattr(prop.NominalValue, "wrappedValue", None)
                    records.append({
                        "GUID": guid,
                        "Element Type": "IfcWall",
                        "Name": name,
                        "ObjectType": obj_type,
                        "Storey": storey,
                        "Material": material,
                        "Data Type": "Property",
                        "Set Name": prop_def.Name,
                        "Attribute Name": prop.Name,
                        "Value": val
                    })

        # --- Quantity Sets ---
        elif prop_def.is_a("IfcElementQuantity") and prop_def.Name in target_qsets:
            for quantity in prop_def.Quantities:
                for attr in dir(quantity):
                    if attr.endswith("Value") and quantity.Name in target_quantities:
                        val = getattr(quantity, attr)
                        if val is not None:
                            records.append({
                                "GUID": guid,
                                "Element Type": "IfcWall",
                                "Name": name,
                                "ObjectType": obj_type,
                                "Storey": storey,
                                "Material": material,
                                "Data Type": "Quantity",
                                "Set Name": prop_def.Name,
                                "Attribute Name": quantity.Name,
                                "Value": val
                            })

# === Convert to DataFrame ===
df = pd.DataFrame(records)

# === Export ===
if EXPORT_FILE.endswith(".csv"):
    df.to_csv(EXPORT_FILE, index=False)
else:
    df.to_excel(EXPORT_FILE, index=False)

print(f"✅ Enriched wall data exported to: {EXPORT_FILE}")
