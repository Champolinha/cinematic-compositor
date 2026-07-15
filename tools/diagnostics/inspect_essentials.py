import os

import bpy


def find_essentials_file():
    """Locate Blender's compositor essentials file on the current machine."""
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    candidates = [
        os.path.join(
            os.path.dirname(bpy.app.binary_path),
            version,
            "datafiles",
            "assets",
            "nodes",
            "compositing_nodes_essentials.blend",
        )
    ]
    for resource_type in ("USER", "LOCAL", "SYSTEM"):
        resource_path = bpy.utils.resource_path(resource_type)
        if resource_path:
            candidates.append(
                os.path.join(
                    resource_path,
                    "datafiles",
                    "assets",
                    "nodes",
                    "compositing_nodes_essentials.blend",
                )
            )
    return next((path for path in candidates if os.path.exists(path)), None)


filepath = find_essentials_file()
print("\n--- INSPECTING COMPOSITING ESSENTIALS ---")

if not filepath:
    print("Could not find compositing_nodes_essentials.blend")
else:
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        print(f"Node Groups in essentials file:")
        for name in data_from.node_groups:
            print(f"  '{name}'")
print("------------------------------------------\n")
