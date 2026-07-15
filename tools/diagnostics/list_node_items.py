import bpy
import nodeitems_utils

print("\n--- COMPOSITOR MENU ITEMS ---")
# To iteration over compositor node categories, we iterate over registered categories
try:
    for cat in nodeitems_utils.node_categories_iter(bpy.context):
        # We only want compositor categories
        # node_categories_iter doesn't take category ID as argument in newer versions, 
        # it just returns all of them. So we check cat.poll
        # Let's inspect cat properties
        print(f"Category: {cat.label} (ID: {cat.identifier})")
        try:
            for item in cat.items(bpy.context):
                if hasattr(item, "nodetype"):
                    print(f"  Label: '{item.label}', Type: '{item.nodetype}'")
                elif hasattr(item, "label"):
                    print(f"  Label: '{item.label}' (Group/Custom)")
        except Exception as e:
            print(f"  Error getting items: {e}")
except Exception as e:
    print(f"Error iterating categories: {e}")

# Let's also search in bpy.data.node_groups to see if there are any built-in template groups 
# in the startup file (like essential assets)
print("\n--- STARTUP NODE GROUPS ---")
for g in bpy.data.node_groups:
    print(f"  Group: '{g.name}', Type: {g.type}")

print("-----------------------------\n")
