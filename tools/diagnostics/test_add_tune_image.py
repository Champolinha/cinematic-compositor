import bpy

tree = bpy.data.node_groups.new(name="TestTree", type='CompositorNodeTree')
print("\n--- TUNE IMAGE ADDITION TEST ---")
try:
    node = tree.nodes.new(type='CompositorNodeTuneImage')
    print("SUCCESS: Created CompositorNodeTuneImage!")
    print(f"Attributes: {dir(node)}")
    print("INPUTS:")
    for s in node.inputs:
         print(f"  name: '{s.name}', type: {s.type}, default: {getattr(s, 'default_value', 'N/A')}")
except Exception as e:
    print(f"FAILED: {e}")
print("--------------------------------\n")
