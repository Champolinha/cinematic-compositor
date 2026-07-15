import bpy

print("\n--- TUNE NODE SEARCH ---")
# 1. Search in bpy.types for classes containing "tune" or "clarity" or "sharpen"
matching_types = []
for name in dir(bpy.types):
    if "tune" in name.lower() or "clarity" in name.lower() or "sharpen" in name.lower():
        matching_types.append(name)
print(f"Matching classes in bpy.types: {matching_types}")

# 2. Let's create a temporary compositor tree and list all possible node type strings we can add
# We can do this by trying to create a node of type that raises an error, which shows the list of valid node types!
tree = bpy.data.node_groups.new(name="TestTree", type='CompositorNodeTree')
try:
    tree.nodes.new("NonExistentNode")
except Exception as e:
    err_str = str(e)
    # The error string might contain the list of all valid node types!
    # Let's check if it lists them.
    # In some versions of Blender, it lists all valid types. Let's print the error message.
    print(f"Error message: {err_str}")
    
# 3. Let's list all subclasses of CompositorNode and print them if they are new
compositor_classes = []
for name in dir(bpy.types):
    if name.startswith("CompositorNode"):
        compositor_classes.append(name)
        
# Let's print any classes that might have been added recently or contain "tune"
for name in compositor_classes:
    if "tune" in name.lower() or "color" in name.lower() or "image" in name.lower() or "creative" in name.lower() or "filter" in name.lower():
        print(f"CompositorNode class: {name}")

print("------------------------\n")
