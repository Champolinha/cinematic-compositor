bl_info = {
    "name": "Custom Cinematic Compositor",
    "author": "Antigravity AI / Origami Designer",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "Compositor > Sidebar > Cinematic | 3D Viewport > Sidebar > Cinematic",
    "description": "Professional post-processing effects and film grading in Blender sidebar.",
    "category": "Compositing",
}

import bpy

# ==========================================
# NODE UTILITIES & SUPPORT FUNCTIONS
# ==========================================

def get_socket(node, name_or_idx, is_input=True):
    """Safely retrieves a node socket by name (case-insensitive) or index, supporting different versions of Blender."""
    sockets = node.inputs if is_input else node.outputs
    if isinstance(name_or_idx, str):
        socket = sockets.get(name_or_idx)
        if socket:
            return socket
        name_lower = name_or_idx.lower()
        for s in sockets:
            if name_lower in s.name.lower():
                return s
        return sockets[0] if len(sockets) > 0 else None
    else:
        return sockets[name_or_idx] if len(sockets) > name_or_idx else None

def get_socket_by_candidates(node, candidate_names, is_input=True):
    """Retrieves a node socket checking multiple candidate names, supporting ShaderNodeMix in 5.0+."""
    sockets = node.inputs if is_input else node.outputs
    
    # Phase 1: Try exact matches for all candidates
    for name in candidate_names:
        if isinstance(name, int):
            if len(sockets) > name:
                return sockets[name]
            continue
            
        # Special case: ShaderNodeMix color sockets
        if node.type == 'MIX' and name in ['A', 'B', 'Factor', 'Result']:
            for s in sockets:
                if s.name == name and s.type == 'RGBA':
                    return s
                    
        socket = sockets.get(name)
        if socket:
            return socket
            
    # Phase 2: Try case-insensitive exact matches for all candidates
    for name in candidate_names:
        if isinstance(name, int):
            continue
        name_lower = name.lower()
        for s in sockets:
            if s.name.lower() == name_lower:
                return s
                
    # Phase 3: Try substring matches (only as a last resort)
    for name in candidate_names:
        if isinstance(name, int):
            continue
        name_lower = name.lower()
        for s in sockets:
            if name_lower in s.name.lower():
                return s
                
    return sockets[0] if len(sockets) > 0 else None

def link_nodes(links, from_node, from_socket_id, to_node, to_socket_id):
    """Safely creates a link between two nodes."""
    from_socket = get_socket(from_node, from_socket_id, is_input=False)
    to_socket = get_socket(to_node, to_socket_id, is_input=True)
    if from_socket and to_socket:
        links.new(from_socket, to_socket)

def link_nodes_by_candidates(links, from_node, from_sockets, to_node, to_sockets):
    """Links nodes using candidate names to bridge version differences (like Color1 -> A)."""
    from_sock = get_socket_by_candidates(from_node, from_sockets, is_input=False)
    to_sock = get_socket_by_candidates(to_node, to_sockets, is_input=True)
    if from_sock and to_sock:
        links.new(from_sock, to_sock)

def get_essentials_blend_path():
    """Finds the built-in essentials assets blend file in the Blender installation."""
    import os
    bin_dir = os.path.dirname(bpy.app.binary_path)
    version_str = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    path1 = os.path.join(bin_dir, version_str, 'datafiles', 'assets', 'nodes', 'compositing_nodes_essentials.blend')
    if os.path.exists(path1):
        return path1
    for path_type in ['USER', 'LOCAL', 'SYSTEM']:
        try:
            res_path = bpy.utils.resource_path(path_type)
            path2 = os.path.join(res_path, 'datafiles', 'assets', 'nodes', 'compositing_nodes_essentials.blend')
            if os.path.exists(path2):
                return path2
        except:
            pass
    return None

def get_or_import_tune_image_group():
    """Imports the built-in 'Tune Image' essential node group from Blender's installation if not already loaded."""
    existing = bpy.data.node_groups.get("Tune Image")
    if existing:
        return existing
        
    blend_path = get_essentials_blend_path()
    if not blend_path:
        return None
        
    try:
        with bpy.data.libraries.load(blend_path) as (data_from, data_to):
            if "Tune Image" in data_from.node_groups:
                data_to.node_groups.append("Tune Image")
        return bpy.data.node_groups.get("Tune Image")
    except Exception as e:
        print(f"Failed to append 'Tune Image' node group: {e}")
        return None

# ==========================================
# NODE GROUP INITIALIZATION
# ==========================================

def get_or_create_group_tree():
    """Creates and configures the internal Cinematic Compositor Node Group."""
    group_tree = bpy.data.node_groups.get("CinematicCompositorGroup")
    
    # Check if the group already exists and is fully populated
    if group_tree:
        expected_nodes = [
            "CinematicLens", "CinematicBloom", "CinematicStreaks", "CinematicGhosts",
            "CinematicSharpen", "CinematicRGBCurves", "CinematicColorBalance",
            "CinematicBrightContrast", "CinematicHSV", "CinematicTuneImage", "CinematicHueCorrect",
            "CinematicVignetteMask", "CinematicVignetteBlur", "CinematicVignetteMix",
            "CinematicGrainTexture", "CinematicGrainMix"
        ]
        has_all = all(group_tree.nodes.get(name) is not None for name in expected_nodes)
        if has_all:
            return group_tree
            
        # Rebuild incomplete/broken group
        group_tree.nodes.clear()
        if hasattr(group_tree, "interface"):
            group_tree.interface.clear()
        else:
            group_tree.inputs.clear()
            group_tree.outputs.clear()
    else:
        group_tree = bpy.data.node_groups.new(name="CinematicCompositorGroup", type='CompositorNodeTree')
    
    # Setup group input and output sockets (compat with Blender 3.x and 4.x/5.x)
    is_blender_4 = hasattr(group_tree, "interface")
    if is_blender_4:
        group_tree.interface.new_socket(name="Image", in_out='INPUT', socket_type='NodeSocketColor')
        group_tree.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    else:
        group_tree.inputs.new('NodeSocketColor', "Image")
        group_tree.outputs.new('NodeSocketColor', "Image")
        
    input_node = group_tree.nodes.new('NodeGroupInput')
    input_node.name = "GroupInput"
    input_node.location = (-800, 0)
    
    output_node = group_tree.nodes.new('NodeGroupOutput')
    output_node.name = "GroupOutput"
    output_node.location = (1900, 0)
    
    is_blender_5 = hasattr(bpy.context.scene, "compositing_node_group") and not hasattr(bpy.context.scene, "node_tree")
    
    # 1. Lens Distortion (Chromatic Aberration & Distortion)
    lens = group_tree.nodes.new('CompositorNodeLensdist')
    lens.name = "CinematicLens"
    if hasattr(lens, "use_projector"):
        lens.use_projector = True
    lens.location = (-600, 0)
    
    # 2. Flare A (Bloom / Fog Glow)
    glare_bloom = group_tree.nodes.new('CompositorNodeGlare')
    glare_bloom.name = "CinematicBloom"
    if hasattr(glare_bloom, "glare_type"):
        glare_bloom.glare_type = 'FOG_GLOW'
        glare_bloom.quality = 'HIGH'
    else:
        glare_bloom.inputs['Type'].default_value = 'Fog Glow'
        glare_bloom.inputs['Quality'].default_value = 'High'
    glare_bloom.location = (-400, 0)
    
    # 3. Flare B (Streaks / Anamorphic Streaks)
    glare_streaks = group_tree.nodes.new('CompositorNodeGlare')
    glare_streaks.name = "CinematicStreaks"
    if hasattr(glare_streaks, "glare_type"):
        glare_streaks.glare_type = 'STREAKS'
        glare_streaks.quality = 'HIGH'
    else:
        glare_streaks.inputs['Type'].default_value = 'Streaks'
        glare_streaks.inputs['Quality'].default_value = 'High'
    glare_streaks.location = (-200, 0)
    
    # 4. Flare C (Ghosts / Reflections)
    glare_ghosts = group_tree.nodes.new('CompositorNodeGlare')
    glare_ghosts.name = "CinematicGhosts"
    if hasattr(glare_ghosts, "glare_type"):
        glare_ghosts.glare_type = 'GHOSTS'
        glare_ghosts.quality = 'HIGH'
    else:
        glare_ghosts.inputs['Type'].default_value = 'Ghosts'
        glare_ghosts.inputs['Quality'].default_value = 'High'
    glare_ghosts.location = (0, 0)
    
    # 5. Detail Sharpen
    sharpen = group_tree.nodes.new('CompositorNodeFilter')
    sharpen.name = "CinematicSharpen"
    if hasattr(sharpen, "filter_type"):
        sharpen.filter_type = 'SHARPEN'
    else:
        type_socket = sharpen.inputs.get('Type')
        if type_socket:
            type_socket.default_value = 'Box Sharpen'
    sharpen.location = (200, 0)
    
    # 6. Film S-Curve (RGB Curves)
    if is_blender_5:
        rgb_curves = group_tree.nodes.new('CompositorNodeCurveRGB')
    else:
        rgb_curves = group_tree.nodes.new('CompositorNodeRGBCurves')
    rgb_curves.name = "CinematicRGBCurves"
    rgb_curves.location = (400, 0)
    
    # 7. Color Balance (Color Grading / Looks)
    color_balance = group_tree.nodes.new('CompositorNodeColorBalance')
    color_balance.name = "CinematicColorBalance"
    if hasattr(color_balance, "correction_method"):
        color_balance.correction_method = 'LIFT_GAMMA_GAIN'
    else:
        type_socket = color_balance.inputs.get('Type')
        if type_socket:
            type_socket.default_value = 'Lift/Gamma/Gain'
    color_balance.location = (650, 0)
    
    # 8. Brightness/Contrast (Exposure & Contrast)
    bright_contrast = group_tree.nodes.new('CompositorNodeBrightContrast')
    bright_contrast.name = "CinematicBrightContrast"
    bright_contrast.location = (900, 0)
    
    # 9. HSV Saturation
    hsv = group_tree.nodes.new('CompositorNodeHueSat')
    hsv.name = "CinematicHSV"
    hsv.location = (1100, 0)
    
    # 9.5 Tune Image (Imported group node)
    tune_node = group_tree.nodes.new('CompositorNodeGroup')
    tune_node.name = "CinematicTuneImage"
    tune_group = get_or_import_tune_image_group()
    if tune_group:
        tune_node.node_tree = tune_group
    tune_node.location = (1200, 150)
    
    # 10. Selective Hue Saturation (Autumn / Red Separation)
    hue_correct = group_tree.nodes.new('CompositorNodeHueCorrect')
    hue_correct.name = "CinematicHueCorrect"
    hue_correct.location = (1400, 0)
    
    # 11. Vignette System
    vig_mask = group_tree.nodes.new('CompositorNodeEllipseMask')
    vig_mask.name = "CinematicVignetteMask"
    vig_mask.location = (1200, -300)
    
    vig_blur = group_tree.nodes.new('CompositorNodeBlur')
    vig_blur.name = "CinematicVignetteBlur"
    if hasattr(vig_blur, "filter_type"):
        vig_blur.filter_type = 'FAST_GAUSSIAN'
        vig_blur.use_relative = False
    else:
        type_socket = vig_blur.inputs.get('Type')
        if type_socket:
            type_socket.default_value = 'Gaussian'
    vig_blur.location = (1400, -300)
    
    if is_blender_5:
        vig_mix = group_tree.nodes.new('ShaderNodeMix')
        vig_mix.data_type = 'RGBA'
        vig_mix.blend_type = 'MULTIPLY'
        b_socket = get_socket_by_candidates(vig_mix, ['B'], is_input=True)
        if b_socket:
            b_socket.default_value = (0.0, 0.0, 0.0, 1.0)
    else:
        vig_mix = group_tree.nodes.new('CompositorNodeMixRGB')
        vig_mix.blend_type = 'MULTIPLY'
        vig_mix.inputs['Color2'].default_value = (0.0, 0.0, 0.0, 1.0)
        
    vig_mix.name = "CinematicVignetteMix"
    vig_mix.location = (1500, 0)
    
    # 12. Film Grain System
    if is_blender_5:
        grain_tex_node = group_tree.nodes.new('ShaderNodeTexNoise')
        detail_socket = grain_tex_node.inputs.get('Detail')
        if detail_socket:
            detail_socket.default_value = 2.0
        roughness_socket = grain_tex_node.inputs.get('Roughness')
        if roughness_socket:
            roughness_socket.default_value = 0.5
    else:
        grain_tex = bpy.data.textures.get("CinematicFilmGrain")
        if not grain_tex:
            grain_tex = bpy.data.textures.new("CinematicFilmGrain", 'CLOUDS')
            grain_tex.noise_scale = 0.01
            grain_tex.noise_depth = 2
            
        grain_tex_node = group_tree.nodes.new('CompositorNodeTexture')
        grain_tex_node.texture = grain_tex
        
    grain_tex_node.name = "CinematicGrainTexture"
    grain_tex_node.location = (1500, -300)
    
    if is_blender_5:
        grain_mix = group_tree.nodes.new('ShaderNodeMix')
        grain_mix.data_type = 'RGBA'
        grain_mix.blend_type = 'OVERLAY'
    else:
        grain_mix = group_tree.nodes.new('CompositorNodeMixRGB')
        grain_mix.blend_type = 'OVERLAY'
        
    grain_mix.name = "CinematicGrainMix"
    grain_mix.location = (1700, 0)
    
    # Connect pipeline links
    links = group_tree.links
    link_nodes_by_candidates(links, input_node, [0, 'Image'], lens, ['Image'])
    link_nodes_by_candidates(links, lens, ['Image'], glare_bloom, ['Color', 'Image'])
    link_nodes_by_candidates(links, glare_bloom, ['Color', 'Image'], glare_streaks, ['Color', 'Image'])
    link_nodes_by_candidates(links, glare_streaks, ['Color', 'Image'], glare_ghosts, ['Color', 'Image'])
    link_nodes_by_candidates(links, glare_ghosts, ['Color', 'Image'], sharpen, ['Image'])
    link_nodes_by_candidates(links, sharpen, ['Image'], rgb_curves, ['Image'])
    link_nodes_by_candidates(links, rgb_curves, ['Image', 'Color'], color_balance, ['Color'])
    link_nodes_by_candidates(links, color_balance, ['Color'], bright_contrast, ['Color'])
    link_nodes_by_candidates(links, bright_contrast, ['Color'], hsv, ['Color'])
    
    # Connect Tune Image node if supported by Blender version
    tune_node = group_tree.nodes.get("CinematicTuneImage")
    has_tune = tune_node and tune_node.node_tree is not None
    if has_tune:
        link_nodes_by_candidates(links, hsv, ['Color'], tune_node, ['Image'])
        link_nodes_by_candidates(links, tune_node, ['Image'], hue_correct, ['Image'])
    else:
        link_nodes_by_candidates(links, hsv, ['Color'], hue_correct, ['Image'])
        
    link_nodes_by_candidates(links, hue_correct, ['Image', 'Color'], vig_mix, ['Color1', 'A'])
    link_nodes_by_candidates(links, vig_mix, ['Color', 'Result'], grain_mix, ['Color1', 'A'])
    link_nodes_by_candidates(links, grain_mix, ['Color', 'Result'], output_node, [0, 'Image'])
    
    # Connect Vignette sub-network
    link_nodes_by_candidates(links, vig_mask, ['Mask'], vig_blur, ['Image'])
    link_nodes_by_candidates(links, vig_blur, ['Image'], vig_mix, ['Color2', 'B'])
    
    # Connect Grain sub-network
    link_nodes_by_candidates(links, grain_tex_node, ['Color', 'Value'], grain_mix, ['Color2', 'B'])
    
    return group_tree

# ==========================================
# NODE PLACEMENT & CONNECTIONS
# ==========================================

def get_scene_node_tree(scene):
    """Safely returns the compositor node tree of the scene, supporting Blender 5.0+ changes."""
    if hasattr(scene, "compositing_node_group"):
        return scene.compositing_node_group
    elif hasattr(scene, "node_tree"):
        return scene.node_tree
    return None

def get_output_node(node_tree):
    """Finds the active composite output node (COMPOSITE or GROUP_OUTPUT in Blender 5.0+)."""
    for n in node_tree.nodes:
        if n.type == 'COMPOSITE':
            return n
    for n in node_tree.nodes:
        if n.type == 'GROUP_OUTPUT':
            return n
    return None

def get_or_create_output_node(node_tree):
    """Safely retrieves or creates the appropriate active output node depending on the Blender version."""
    node = get_output_node(node_tree)
    if node:
        return node
        
    is_blender_5 = hasattr(bpy.context.scene, "compositing_node_group") and not hasattr(bpy.context.scene, "node_tree")
    if is_blender_5:
        node = node_tree.nodes.new('NodeGroupOutput')
        if hasattr(node_tree, "interface"):
            has_output = False
            # Check items_tree (Blender 4.0+) first to avoid calling standard items() method on bpy_struct
            items = getattr(node_tree.interface, "items_tree", [])
            for item in items:
                if hasattr(item, "in_out") and item.in_out == 'OUTPUT':
                    has_output = True
                    break
            if not has_output:
                node_tree.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    else:
        node = node_tree.nodes.new('CompositorNodeComposite')
    return node

def insert_cinematic_node(scene):
    """Inserts the Cinematic Compositor node group between the Render Layers and active Output."""
    node_tree = get_scene_node_tree(scene)
    if not node_tree:
        if hasattr(scene, "compositing_node_group"):
            node_tree = bpy.data.node_groups.new(name="Compositing Node Tree", type='CompositorNodeTree')
            scene.compositing_node_group = node_tree
        else:
            scene.use_nodes = True
            node_tree = scene.node_tree
            
    if not node_tree:
        return

    # Check if node group already exists in compositor
    cin_node = None
    for n in node_tree.nodes:
        if n.type == 'GROUP' and n.node_tree and n.node_tree.name == "CinematicCompositorGroup":
            cin_node = n
            break

    if not cin_node:
        group_tree = get_or_create_group_tree()
        cin_node = node_tree.nodes.new('CompositorNodeGroup')
        cin_node.node_tree = group_tree
        cin_node.name = "CinematicCompositorInstance"
        cin_node.label = "Cinematic Compositor"

    composite_node = get_output_node(node_tree)
    if not composite_node:
        composite_node = get_or_create_output_node(node_tree)

    if composite_node:
        cin_node.location = (composite_node.location.x - 250, composite_node.location.y)
        image_input = get_socket(composite_node, "Image", is_input=True)
        if not image_input and len(composite_node.inputs) > 0:
            image_input = composite_node.inputs[0]
        
        # Intercept existing connection
        if image_input and image_input.is_linked:
            source_socket = image_input.links[0].from_socket
            if source_socket.node != cin_node:
                node_tree.links.new(source_socket, cin_node.inputs[0])
        else:
            # Connect to render layers (create if missing to enable viewport preview in empty scenes)
            rlayers = None
            for n in node_tree.nodes:
                if n.type == 'RLAYERS':
                    rlayers = n
                    break
            if not rlayers:
                rlayers = node_tree.nodes.new('CompositorNodeRLayers')
                rlayers.location = (cin_node.location.x - 300, cin_node.location.y)
                
            rlayers_out = get_socket(rlayers, "Image", is_input=False)
            if rlayers_out and len(cin_node.inputs) > 0:
                node_tree.links.new(rlayers_out, cin_node.inputs[0])
                
        # Link group node output to composite node input
        if image_input and len(cin_node.outputs) > 0:
            node_tree.links.new(cin_node.outputs[0], image_input)

        # Update viewer node for backdrop rendering
        viewer_node = None
        for n in node_tree.nodes:
            if n.type == 'VIEWER':
                viewer_node = n
                break
        if viewer_node:
            viewer_input = get_socket(viewer_node, "Image", is_input=True)
            if viewer_input and len(cin_node.outputs) > 0:
                node_tree.links.new(cin_node.outputs[0], viewer_input)

def remove_cinematic_node(scene):
    """Safely removes the Cinematic Compositor node group and restores direct connections."""
    node_tree = get_scene_node_tree(scene)
    if not node_tree:
        return
        
    cin_node = None
    for n in node_tree.nodes:
        if n.type == 'GROUP' and n.node_tree and n.node_tree.name == "CinematicCompositorGroup":
            cin_node = n
            break
            
    if cin_node:
        source_socket = None
        if len(cin_node.inputs) > 0 and cin_node.inputs[0].is_linked:
            source_socket = cin_node.inputs[0].links[0].from_socket
            
        target_sockets = []
        if len(cin_node.outputs) > 0 and cin_node.outputs[0].is_linked:
            for link in cin_node.outputs[0].links:
                target_sockets.append(link.to_socket)
                
        # Reconnect preceding node directly to outputs
        if source_socket:
            for target in target_sockets:
                node_tree.links.new(source_socket, target)
                
        node_tree.nodes.remove(cin_node)

# ==========================================
# NODE PARAMETERS MANAGEMENT (UPDATE LOOPS)
# ==========================================

def set_glare_properties(glare_node, strength, threshold, size_or_fade=None, count=None, angle=None):
    """Safely assigns glare properties handling differences between pre-5.0 (properties) and 5.0+ (sockets)."""
    if hasattr(glare_node, "glare_type"):
        glare_node.mix = (strength * 2.0) - 1.0
        glare_node.threshold = threshold
        if glare_node.glare_type == 'FOG_GLOW' and size_or_fade is not None:
            glare_node.size = int(size_or_fade)
        elif glare_node.glare_type == 'STREAKS':
            if count is not None:
                glare_node.streaks = count
            if angle is not None:
                glare_node.angle_offset = angle
            if size_or_fade is not None:
                glare_node.fade = size_or_fade
        elif glare_node.glare_type == 'GHOSTS' and count is not None:
            glare_node.ghosts = count
    else:
        if 'Strength' in glare_node.inputs:
            glare_node.inputs['Strength'].default_value = strength
        if 'Threshold' in glare_node.inputs:
            glare_node.inputs['Threshold'].default_value = threshold
            
        glare_type_str = glare_node.inputs['Type'].default_value
        if glare_type_str == 'Fog Glow' and size_or_fade is not None:
            mapped_size = (size_or_fade - 6) / 3.0
            glare_node.inputs['Size'].default_value = max(0.0, min(1.0, mapped_size))
        elif glare_type_str == 'Streaks':
            if count is not None:
                glare_node.inputs['Streaks'].default_value = count
            if angle is not None:
                glare_node.inputs['Streaks Angle'].default_value = angle
            if size_or_fade is not None:
                glare_node.inputs['Fade'].default_value = size_or_fade
        elif glare_type_str == 'Ghosts' and count is not None:
            glare_node.inputs['Streaks'].default_value = count

def update_nodes_from_properties(scene):
    """Synchronizes UI settings with the internal compositor nodes."""
    settings = scene.cinematic_settings
    if not settings.enabled:
        return
        
    group_tree = bpy.data.node_groups.get("CinematicCompositorGroup")
    if not group_tree:
        return
        
    # 1. Lens Distortion
    lens = group_tree.nodes.get("CinematicLens")
    if lens:
        distort_sock = get_socket_by_candidates(lens, ['Distortion', 'Distort'], is_input=True)
        if distort_sock:
            distort_sock.default_value = settings.lens_distortion
        dispersion_sock = get_socket_by_candidates(lens, ['Dispersion'], is_input=True)
        if dispersion_sock:
            dispersion_sock.default_value = settings.chromatic_aberration
        lens.mute = not settings.lens_enabled

    # 2. Flare A (Bloom)
    glare_bloom = group_tree.nodes.get("CinematicBloom")
    if glare_bloom:
        glare_bloom.mute = not settings.bloom_enabled
        set_glare_properties(glare_bloom, settings.bloom_strength, settings.bloom_threshold, size_or_fade=settings.bloom_size)

    # 3. Flare B (Streaks)
    glare_streaks = group_tree.nodes.get("CinematicStreaks")
    if glare_streaks:
        glare_streaks.mute = not settings.streaks_enabled
        set_glare_properties(glare_streaks, settings.streaks_strength, settings.streaks_threshold, size_or_fade=settings.streaks_fade, count=settings.streaks_count, angle=settings.streaks_angle)

    # 4. Flare C (Ghosts)
    glare_ghosts = group_tree.nodes.get("CinematicGhosts")
    if glare_ghosts:
        glare_ghosts.mute = not settings.ghosts_enabled
        set_glare_properties(glare_ghosts, settings.ghosts_strength, settings.ghosts_threshold, count=settings.ghosts_count)

    # 5. Sharpen
    sharpen = group_tree.nodes.get("CinematicSharpen")
    if sharpen:
        sharpen.inputs['Factor'].default_value = settings.sharpen_strength
        sharpen.mute = not settings.sharpen_enabled

    # 6. Film S-Curve (RGB Curves)
    rgb_curves = group_tree.nodes.get("CinematicRGBCurves")
    if rgb_curves:
        rgb_curves.mute = not settings.use_film_look
        # Setup S-Curve points
        curve = rgb_curves.mapping.curves[3]
        while len(curve.points) > 2:
            curve.points.remove(curve.points[1])
        curve.points[0].location = (0.0, 0.0)
        curve.points[1].location = (1.0, 1.0)
        
        if settings.use_film_look:
            curve.points[0].location = (0.0, 0.015)  # Soft raised blacks
            curve.points.new(0.25, 0.16)
            curve.points.new(0.5, 0.5)
            curve.points.new(0.75, 0.84)
            curve.points[1].location = (1.0, 0.985)  # Soft highlights shoulder
        rgb_curves.mapping.update()

    # Base Color Values
    lift = [1.0, 1.0, 1.0]
    gamma = [1.0, 1.0, 1.0]
    gain = [1.0, 1.0, 1.0]
    contrast_offset = 0.0
    saturation_mult = 1.0

    # 7. Apply Preset Looks to Color Balance
    if settings.look_preset == 'TEAL_ORANGE':
        lift = [0.90, 0.95, 1.00]
        gamma = [0.96, 0.98, 1.02]
        gain = [1.14, 1.03, 0.86]
    elif settings.look_preset == 'VINTAGE':
        lift = [1.03, 1.01, 0.97]
        gamma = [1.01, 0.99, 0.96]
        gain = [0.98, 0.96, 0.93]
    elif settings.look_preset == 'WARM':
        lift = [1.00, 0.99, 0.97]
        gamma = [1.04, 1.02, 0.96]
        gain = [1.12, 1.06, 0.91]
    elif settings.look_preset == 'COOL':
        lift = [0.97, 0.99, 1.01]
        gamma = [0.96, 0.98, 1.04]
        gain = [0.91, 0.98, 1.14]
    elif settings.look_preset == 'MONOCHROME':
        contrast_offset = 6.0
        saturation_mult = 0.0
    elif settings.look_preset == 'BLEACH_BYPASS':
        lift = [0.94, 0.94, 0.94]
        gamma = [1.00, 1.00, 1.00]
        gain = [1.06, 1.06, 1.06]
        contrast_offset = 18.0
        saturation_mult = 0.35
    elif settings.look_preset == 'AUTUMN':
        # Green foliage desaturation is handled in Hue Correct
        pass
    elif settings.look_preset == 'RED_SEPARATION':
        # Desaturating other hues is handled in Hue Correct
        contrast_offset = 8.0

    # 8. White Balance Adjustments (Temperature & Tint)
    if settings.temperature != 0.0:
        t = settings.temperature * 0.08
        gamma[0] += t
        gamma[2] -= t
        gain[0] += t * 1.5
        gain[2] -= t * 1.5
        
    if settings.tint != 0.0:
        g = settings.tint * 0.08
        gamma[0] += g * 0.5
        gamma[1] -= g
        gamma[2] += g * 0.5
        gain[0] += g * 0.7
        gain[1] -= g * 1.2
        gain[2] += g * 0.7

    # Apply Color Balance
    color_balance = group_tree.nodes.get("CinematicColorBalance")
    if color_balance:
        if hasattr(color_balance, "lift"):
            for i in range(3):
                color_balance.lift[i] = lift[i]
                color_balance.gamma[i] = gamma[i]
                color_balance.gain[i] = gain[i]
        else:
            # 5.0+ Sockets
            def set_socket(name, rgb):
                for s in color_balance.inputs:
                    if s.name == name and s.type == 'RGBA':
                        s.default_value = (rgb[0], rgb[1], rgb[2], 1.0)
                        break
            set_socket('Lift', lift)
            set_socket('Gamma', gamma)
            set_socket('Gain', gain)

    # 9. Apply Exposure & Contrast
    bright_contrast = group_tree.nodes.get("CinematicBrightContrast")
    if bright_contrast:
        bright_contrast.inputs['Bright'].default_value = settings.exposure
        bright_contrast.inputs['Contrast'].default_value = settings.contrast + contrast_offset

    # 10. Apply Saturation
    hsv = group_tree.nodes.get("CinematicHSV")
    if hsv:
        hsv.inputs['Saturation'].default_value = settings.saturation * saturation_mult

    # 11. Selective Hue Saturation (Autumn / Schindler's list)
    hue_correct = group_tree.nodes.get("CinematicHueCorrect")
    if hue_correct:
        curve = hue_correct.mapping.curves[1]  # Saturation Curve
        expected_x = [0.0, 0.166, 0.333, 0.5, 0.666, 0.833, 1.0]
        
        while len(curve.points) < 7:
            curve.points.new(0.5, 1.0)
        while len(curve.points) > 7:
            curve.points.remove(curve.points[7])
            
        for i, x in enumerate(expected_x):
            curve.points[i].location.x = x

        if settings.look_preset == 'AUTUMN':
            curve.points[0].location.y = 1.00  # Red
            curve.points[1].location.y = 0.50  # Yellow-Orange
            curve.points[2].location.y = 0.08  # Green (desaturated)
            curve.points[3].location.y = 0.35  # Cyan-Green
            curve.points[4].location.y = 0.75  # Blue
            curve.points[5].location.y = 1.00  # Magenta
            curve.points[6].location.y = 1.00  # Red
            hue_correct.mute = False
        elif settings.look_preset == 'RED_SEPARATION':
            curve.points[0].location.y = 1.00  # Red (keep)
            curve.points[1].location.y = 0.00
            curve.points[2].location.y = 0.00
            curve.points[3].location.y = 0.00
            curve.points[4].location.y = 0.00
            curve.points[5].location.y = 0.00
            curve.points[6].location.y = 1.00  # Red (keep)
            hue_correct.mute = False
        else:
            for p in curve.points:
                p.location.y = 1.00
            hue_correct.mute = True
        hue_correct.mapping.update()

    # 12. Vignette Mask Size
    vig_mask = group_tree.nodes.get("CinematicVignetteMask")
    if vig_mask:
        size_socket = vig_mask.inputs.get('Size')
        if size_socket:
            size_socket.default_value = (settings.vignette_size, settings.vignette_size)
        else:
            vig_mask.width = settings.vignette_size
            vig_mask.height = settings.vignette_size

    # 13. Vignette Blur Size
    vig_blur = group_tree.nodes.get("CinematicVignetteBlur")
    if vig_blur:
        size_socket = vig_blur.inputs.get('Size')
        if size_socket:
            size_socket.default_value = (settings.vignette_blur, settings.vignette_blur)
        else:
            vig_blur.size_x = settings.vignette_blur
            vig_blur.size_y = settings.vignette_blur

    # 14. Vignette Mix Strength
    vig_mix = group_tree.nodes.get("CinematicVignetteMix")
    if vig_mix:
        vig_mix.mute = not settings.vignette_enabled
        fac_socket = get_socket_by_candidates(vig_mix, ['Fac', 'Factor'], is_input=True)
        if fac_socket:
            fac_socket.default_value = settings.vignette_strength

    # 15. Film Grain Texture Scale
    grain_tex_node = group_tree.nodes.get("CinematicGrainTexture")
    if grain_tex_node:
        scale_socket = grain_tex_node.inputs.get('Scale')
        if scale_socket:
            scale_socket.default_value = 10.0 / settings.grain_size
        else:
            grain_tex = bpy.data.textures.get("CinematicFilmGrain")
            if grain_tex:
                grain_tex.noise_scale = settings.grain_size

    # 16. Film Grain Mix Strength
    grain_mix = group_tree.nodes.get("CinematicGrainMix")
    if grain_mix:
        grain_mix.mute = not settings.grain_enabled
        fac_socket = get_socket_by_candidates(grain_mix, ['Fac', 'Factor'], is_input=True)
        if fac_socket:
            fac_socket.default_value = settings.grain_strength

    # 17. Tune Image Settings
    tune_node = group_tree.nodes.get("CinematicTuneImage")
    if tune_node:
        tune_node.mute = not settings.tune_enabled
        if not tune_node.mute and tune_node.node_tree is not None:
            # Set properties on the group node inputs
            def set_tune_sock(name, val):
                sock = tune_node.inputs.get(name)
                if sock:
                    sock.default_value = val
            set_tune_sock('Contrast', settings.tune_contrast)
            set_tune_sock('Color Boost', settings.tune_color_boost)
            set_tune_sock('Clarity', settings.tune_clarity)
            set_tune_sock('Detail', settings.tune_detail)
            set_tune_sock('Sharpen', settings.tune_sharpen)
            set_tune_sock('Preserve Colors', settings.tune_preserve_colors)

def update_compositor_callback(self, context):
    update_nodes_from_properties(context.scene)

# ==========================================
# PROPERTIES DEFINITIONS
# ==========================================

class CinematicSettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name="Enabled",
        default=False,
        update=update_compositor_callback
    )
    
    # Presets Look
    look_preset: bpy.props.EnumProperty(
        name="Preset Look",
        items=[
            ('NONE', 'None (Default)', 'Original render settings'),
            ('TEAL_ORANGE', 'Teal & Orange', 'Classical cinematic contrast look'),
            ('VINTAGE', 'Vintage Film', 'Faded film look with warm cast'),
            ('WARM', 'Cinematic Warm', 'Golden sunset film look'),
            ('COOL', 'Cinematic Cool', 'Sci-fi thriller cool blue look'),
            ('AUTUMN', 'Autumn Foliage', 'Skyfall style look desaturating green and yellow vegetation'),
            ('BLEACH_BYPASS', 'Bleach Bypass', 'Fincher style look with high contrast and faded colors'),
            ('MONOCHROME', 'Monochrome B&W', 'High contrast monochrome cinema look'),
            ('RED_SEPARATION', 'Red Separation', 'Isolates and preserves reds, desaturating all other colors'),
        ],
        default='NONE',
        update=update_compositor_callback
    )
    
    use_film_look: bpy.props.BoolProperty(
        name="Film S-Curve",
        description="Applies a filmic S-curve to raise blacks and roll off highlights",
        default=False,
        update=update_compositor_callback
    )
    
    # Color Correction Controls
    exposure: bpy.props.FloatProperty(
        name="Exposure",
        min=-3.0, max=3.0, default=0.0,
        update=update_compositor_callback
    )
    contrast: bpy.props.FloatProperty(
        name="Contrast",
        min=-50.0, max=50.0, default=0.0,
        update=update_compositor_callback
    )
    saturation: bpy.props.FloatProperty(
        name="Saturation",
        min=0.0, max=2.0, default=1.0,
        update=update_compositor_callback
    )
    temperature: bpy.props.FloatProperty(
        name="Temperature",
        description="Warm yellow tones vs Cool blue tones",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    tint: bpy.props.FloatProperty(
        name="Tint",
        description="Magenta vs Green tint balance",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    
    # Flare A: Bloom (Fog Glow)
    bloom_enabled: bpy.props.BoolProperty(
        name="Bloom Enabled",
        default=False,
        update=update_compositor_callback
    )
    bloom_strength: bpy.props.FloatProperty(
        name="Bloom Intensity",
        min=0.0, max=1.0, default=0.3,
        update=update_compositor_callback
    )
    bloom_threshold: bpy.props.FloatProperty(
        name="Bloom Threshold",
        description="Brightness threshold above which pixels glow",
        min=0.0, max=10.0, default=0.8,
        update=update_compositor_callback
    )
    bloom_size: bpy.props.IntProperty(
        name="Bloom Size",
        min=6, max=9, default=8,
        update=update_compositor_callback
    )
    
    # Flare B: Streaks (Anamorphic)
    streaks_enabled: bpy.props.BoolProperty(
        name="Streaks Enabled",
        default=False,
        update=update_compositor_callback
    )
    streaks_strength: bpy.props.FloatProperty(
        name="Streaks Intensity",
        min=0.0, max=1.0, default=0.20,
        update=update_compositor_callback
    )
    streaks_threshold: bpy.props.FloatProperty(
        name="Streaks Threshold",
        min=0.0, max=10.0, default=1.0,
        update=update_compositor_callback
    )
    streaks_count: bpy.props.IntProperty(
        name="Streaks Count",
        min=2, max=16, default=4,
        update=update_compositor_callback
    )
    streaks_angle: bpy.props.IntProperty(
        name="Streaks Angle",
        description="Angle offset for flares in degrees",
        min=0, max=180, default=0,
        update=update_compositor_callback
    )
    streaks_fade: bpy.props.FloatProperty(
        name="Streaks Fade",
        min=0.0, max=1.0, default=0.7,
        update=update_compositor_callback
    )
    
    # Flare C: Ghosts (Lens Reflections)
    ghosts_enabled: bpy.props.BoolProperty(
        name="Ghosts Enabled",
        default=False,
        update=update_compositor_callback
    )
    ghosts_strength: bpy.props.FloatProperty(
        name="Ghosts Intensity",
        min=0.0, max=1.0, default=0.15,
        update=update_compositor_callback
    )
    ghosts_threshold: bpy.props.FloatProperty(
        name="Ghosts Threshold",
        min=0.0, max=10.0, default=1.5,
        update=update_compositor_callback
    )
    ghosts_count: bpy.props.IntProperty(
        name="Ghosts Count",
        min=2, max=8, default=4,
        update=update_compositor_callback
    )
    
    # Lens distortion and sharpening
    lens_enabled: bpy.props.BoolProperty(
        name="Lens Distortion Enabled",
        default=False,
        update=update_compositor_callback
    )
    chromatic_aberration: bpy.props.FloatProperty(
        name="Chromatic Dispersion",
        description="Chromatic aberration color splitting dispersion amount",
        min=0.0, max=0.2, default=0.01,
        update=update_compositor_callback
    )
    lens_distortion: bpy.props.FloatProperty(
        name="Lens Distortion",
        min=-0.2, max=0.2, default=0.0,
        update=update_compositor_callback
    )
    sharpen_enabled: bpy.props.BoolProperty(
        name="Sharpen Enabled",
        default=False,
        update=update_compositor_callback
    )
    sharpen_strength: bpy.props.FloatProperty(
        name="Sharpen Detail",
        min=0.0, max=1.0, default=0.5,
        update=update_compositor_callback
    )
    
    # Vignette settings
    vignette_enabled: bpy.props.BoolProperty(
        name="Vignette Enabled",
        default=False,
        update=update_compositor_callback
    )
    vignette_strength: bpy.props.FloatProperty(
        name="Vignette Strength",
        min=0.0, max=1.0, default=0.5,
        update=update_compositor_callback
    )
    vignette_size: bpy.props.FloatProperty(
        name="Vignette Size",
        min=0.1, max=1.5, default=0.8,
        update=update_compositor_callback
    )
    vignette_blur: bpy.props.IntProperty(
        name="Vignette Blur",
        min=10, max=500, default=150,
        update=update_compositor_callback
    )
    
    # Grain settings
    grain_enabled: bpy.props.BoolProperty(
        name="Grain Enabled",
        default=False,
        update=update_compositor_callback
    )
    grain_strength: bpy.props.FloatProperty(
        name="Grain Strength",
        min=0.0, max=0.5, default=0.05,
        update=update_compositor_callback
    )
    grain_size: bpy.props.FloatProperty(
        name="Grain Scale",
        min=0.001, max=0.1, default=0.01,
        update=update_compositor_callback
    )

    # Tune Image settings (Blender 5.0+)
    tune_enabled: bpy.props.BoolProperty(
        name="Tune Image Enabled",
        default=False,
        update=update_compositor_callback
    )
    tune_contrast: bpy.props.FloatProperty(
        name="Contrast",
        min=-5.0, max=5.0, default=0.0,
        update=update_compositor_callback
    )
    tune_color_boost: bpy.props.FloatProperty(
        name="Color Boost",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    tune_clarity: bpy.props.FloatProperty(
        name="Clarity",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    tune_detail: bpy.props.FloatProperty(
        name="Detail",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    tune_sharpen: bpy.props.FloatProperty(
        name="Sharpen",
        min=-1.0, max=1.0, default=0.0,
        update=update_compositor_callback
    )
    tune_preserve_colors: bpy.props.BoolProperty(
        name="Preserve Colors",
        default=True,
        update=update_compositor_callback
    )

    # UI Foldout Toggles
    show_presets: bpy.props.BoolProperty(name="Presets", default=True)
    show_tune: bpy.props.BoolProperty(name="Tune Image", default=False)
    show_color: bpy.props.BoolProperty(name="Color Correction", default=False)
    show_flares: bpy.props.BoolProperty(name="Lens Flares & Glow", default=False)
    show_vignette: bpy.props.BoolProperty(name="Vignette", default=False)
    show_grain: bpy.props.BoolProperty(name="Film Grain", default=False)
    show_lens: bpy.props.BoolProperty(name="Lens & Camera Effects", default=False)

# ==========================================
# VIEWPORT COMPOSITOR HELPER
# ==========================================

def set_viewport_compositor_mode(mode):
    """Sets the viewport compositor mode for all active 3D viewports (ALWAYS, CAMERA, or DISABLED)."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if hasattr(space.shading, "use_compositor"):
                            try:
                                space.shading.use_compositor = mode
                            except:
                                pass

# ==========================================
# ADDON OPERATORS
# ==========================================

class SCENE_OT_enable_cinematic_compositor(bpy.types.Operator):
    bl_label = "Enable Cinematic Looks"
    bl_idname = "scene.enable_cinematic_compositor"
    bl_description = "Activates the system and inserts node group in compositor"
    
    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "use_nodes"):
            scene.use_nodes = True
        insert_cinematic_node(scene)
        scene.cinematic_settings.enabled = True
        update_nodes_from_properties(scene)
        
        # Turn on viewport compositor
        set_viewport_compositor_mode('ALWAYS')
        
        node_tree = get_scene_node_tree(scene)
        if node_tree:
            node_tree.update_tag()
        return {'FINISHED'}

class SCENE_OT_disable_cinematic_compositor(bpy.types.Operator):
    bl_label = "Disable Cinematic Looks"
    bl_idname = "scene.disable_cinematic_compositor"
    bl_description = "Temporarily disables and bypasses/removes nodes"
    
    def execute(self, context):
        scene = context.scene
        remove_cinematic_node(scene)
        scene.cinematic_settings.enabled = False
        
        # Turn off viewport compositor
        set_viewport_compositor_mode('DISABLED')
        
        node_tree = get_scene_node_tree(scene)
        if node_tree:
            node_tree.update_tag()
        return {'FINISHED'}

class SCENE_OT_reset_cinematic_compositor(bpy.types.Operator):
    bl_label = "Reset Settings"
    bl_idname = "scene.reset_cinematic_compositor"
    bl_description = "Resets all parameters to their default values"
    
    def execute(self, context):
        settings = context.scene.cinematic_settings
        settings.look_preset = 'NONE'
        settings.use_film_look = False
        settings.exposure = 0.0
        settings.contrast = 0.0
        settings.saturation = 1.0
        settings.temperature = 0.0
        settings.tint = 0.0
        
        settings.bloom_enabled = False
        settings.bloom_strength = 0.3
        settings.bloom_threshold = 0.8
        settings.bloom_size = 8
        
        settings.streaks_enabled = False
        settings.streaks_strength = 0.2
        settings.streaks_threshold = 1.0
        settings.streaks_count = 4
        settings.streaks_angle = 0
        settings.streaks_fade = 0.7
        
        settings.ghosts_enabled = False
        settings.ghosts_strength = 0.15
        settings.ghosts_threshold = 1.5
        settings.ghosts_count = 4
        
        settings.lens_enabled = False
        settings.chromatic_aberration = 0.01
        settings.lens_distortion = 0.0
        
        settings.sharpen_enabled = False
        settings.sharpen_strength = 0.5
        
        settings.vignette_enabled = False
        settings.vignette_strength = 0.5
        settings.vignette_size = 0.8
        settings.vignette_blur = 150
        
        settings.grain_enabled = False
        settings.grain_strength = 0.05
        settings.grain_size = 0.01

        settings.tune_enabled = False
        settings.tune_contrast = 0.0
        settings.tune_color_boost = 0.0
        settings.tune_clarity = 0.0
        settings.tune_detail = 0.0
        settings.tune_sharpen = 0.0
        settings.tune_preserve_colors = True
        
        update_nodes_from_properties(context.scene)
        return {'FINISHED'}

# ==========================================
# INTERFACE UI PANELS
# ==========================================

class COMPOSITOR_PT_cinematic_panel(bpy.types.Panel):
    bl_label = "Cinematic Compositor"
    bl_idname = "COMPOSITOR_PT_cinematic_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cinematic"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.cinematic_settings

        node_tree = get_scene_node_tree(scene)
        if hasattr(scene, "use_nodes"):
            if not scene.use_nodes:
                layout.label(text="Please enable 'Use Nodes' in the Compositor", icon='ERROR')
                return
        else:
            if not node_tree:
                layout.label(text="Please create a new Compositor tree", icon='ERROR')
                return

        # Main Power Toggles
        row = layout.row(align=True)
        if not settings.enabled:
            row.operator("scene.enable_cinematic_compositor", text="Enable Cinematic Looks", icon='PLAY')
        else:
            row.operator("scene.disable_cinematic_compositor", text="Disable Cinematic Looks", icon='PAUSE')
            row.operator("scene.reset_cinematic_compositor", text="", icon='FILE_REFRESH')
            
        if not settings.enabled:
            return

        # 1. Preset looks selection
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_presets", 
                 icon="TRIA_DOWN" if settings.show_presets else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Look Presets", icon='COLOR')
        if settings.show_presets:
            col = box.column(align=True)
            col.prop(settings, "look_preset", text="Preset")
            col.prop(settings, "use_film_look", text="Film S-Curve (Matte Highlights)")

        # 2. Tune Image Section (Blender 5.0+ only)
        tune_node = None
        if node_tree:
            comp_group = bpy.data.node_groups.get("CinematicCompositorGroup")
            if comp_group:
                tune_node = comp_group.nodes.get("CinematicTuneImage")
                
        has_tune_node = tune_node and tune_node.node_tree is not None
        
        if has_tune_node:
            box = layout.box()
            row = box.row()
            row.prop(settings, "show_tune", 
                     icon="TRIA_DOWN" if settings.show_tune else "TRIA_RIGHT", 
                     icon_only=True, emboss=False)
            row.label(text="Tune Image (All-in-One)", icon='IMAGE_DATA')
            row.prop(settings, "tune_enabled", text="")
            if settings.show_tune:
                col = box.column(align=True)
                col.enabled = settings.tune_enabled
                col.prop(settings, "tune_contrast", text="Contrast", slider=True)
                col.prop(settings, "tune_color_boost", text="Color Boost", slider=True)
                col.prop(settings, "tune_clarity", text="Clarity", slider=True)
                col.prop(settings, "tune_detail", text="Detail", slider=True)
                col.prop(settings, "tune_sharpen", text="Sharpen", slider=True)
                col.prop(settings, "tune_preserve_colors", text="Preserve Colors", slider=True)

        # 3. Exposure & Colors
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_color", 
                 icon="TRIA_DOWN" if settings.show_color else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Color Correction & Grading", icon='IMAGE_DATA')
        if settings.show_color:
            col = box.column(align=True)
            col.prop(settings, "exposure", text="Exposure", slider=True)
            col.prop(settings, "contrast", text="Contrast", slider=True)
            col.prop(settings, "saturation", text="Saturation", slider=True)
            
            sub = col.row(align=True)
            sub.prop(settings, "temperature", text="Temp", slider=True)
            sub.prop(settings, "tint", text="Tint", slider=True)

        # 4. Flares system (Bloom, Streaks, Ghosts)
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_flares", 
                 icon="TRIA_DOWN" if settings.show_flares else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Lens Flares & Glow", icon='LIGHT')
        if settings.show_flares:
            # Flare A: Bloom
            col = box.column(align=True)
            row_b = col.row()
            row_b.prop(settings, "bloom_enabled", text="Bloom (Fog Glow)")
            if settings.bloom_enabled:
                sub = col.box()
                sub.prop(settings, "bloom_strength", text="Intensity", slider=True)
                sub.prop(settings, "bloom_threshold", text="Threshold", slider=True)
                sub.prop(settings, "bloom_size", text="Size", slider=True)
                
            # Flare B: Streaks
            col = box.column(align=True)
            row_s = col.row()
            row_s.prop(settings, "streaks_enabled", text="Flare Streaks (Anamorphic)")
            if settings.streaks_enabled:
                sub = col.box()
                sub.prop(settings, "streaks_strength", text="Intensity", slider=True)
                sub.prop(settings, "streaks_threshold", text="Threshold", slider=True)
                sub.prop(settings, "streaks_count", text="Count", slider=True)
                sub.prop(settings, "streaks_angle", text="Angle", slider=True)
                sub.prop(settings, "streaks_fade", text="Fade", slider=True)
                
            # Flare C: Ghosts
            col = box.column(align=True)
            row_g = col.row()
            row_g.prop(settings, "ghosts_enabled", text="Flare Ghosts (Reflections)")
            if settings.ghosts_enabled:
                sub = col.box()
                sub.prop(settings, "ghosts_strength", text="Intensity", slider=True)
                sub.prop(settings, "ghosts_threshold", text="Threshold", slider=True)
                sub.prop(settings, "ghosts_count", text="Count", slider=True)

        # 5. Vignette
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_vignette", 
                 icon="TRIA_DOWN" if settings.show_vignette else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Vignette", icon='SHADING_RENDERED')
        row.prop(settings, "vignette_enabled", text="")
        if settings.show_vignette:
            col = box.column(align=True)
            col.enabled = settings.vignette_enabled
            col.prop(settings, "vignette_strength", text="Strength", slider=True)
            col.prop(settings, "vignette_size", text="Size", slider=True)
            col.prop(settings, "vignette_blur", text="Blur", slider=True)

        # 6. Film Grain
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_grain", 
                 icon="TRIA_DOWN" if settings.show_grain else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Film Grain", icon='TEXTURE')
        row.prop(settings, "grain_enabled", text="")
        if settings.show_grain:
            col = box.column(align=True)
            col.enabled = settings.grain_enabled
            col.prop(settings, "grain_strength", text="Strength", slider=True)
            col.prop(settings, "grain_size", text="Scale", slider=True)

        # 7. Lens distortion and camera properties
        box = layout.box()
        row = box.row()
        row.prop(settings, "show_lens", 
                 icon="TRIA_DOWN" if settings.show_lens else "TRIA_RIGHT", 
                 icon_only=True, emboss=False)
        row.label(text="Lens & Camera Effects", icon='CAMERA_DATA')
        if settings.show_lens:
            col = box.column(align=True)
            
            # Lens Distortion sub-section
            sub1 = col.box()
            sub1.prop(settings, "lens_enabled", text="Lens Distortion")
            if settings.lens_enabled:
                sub1.prop(settings, "lens_distortion", text="Distortion", slider=True)
                sub1.prop(settings, "chromatic_aberration", text="Chromatic Dispersion", slider=True)
                
            # Sharpen sub-section
            sub2 = col.box()
            sub2.prop(settings, "sharpen_enabled", text="Sharpen Detail")
            if settings.sharpen_enabled:
                sub2.prop(settings, "sharpen_strength", text="Sharpen Factor", slider=True)

class VIEW3D_PT_cinematic_panel(bpy.types.Panel):
    """Mirror the sidebar panel into the 3D Viewport for real-time scene updates."""
    bl_label = "Cinematic Compositor"
    bl_idname = "VIEW3D_PT_cinematic_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Cinematic"

    def draw(self, context):
        COMPOSITOR_PT_cinematic_panel.draw(self, context)

# ==========================================
# REGISTER & UNREGISTER ADDON
# ==========================================

classes = (
    CinematicSettings,
    SCENE_OT_enable_cinematic_compositor,
    SCENE_OT_disable_cinematic_compositor,
    SCENE_OT_reset_cinematic_compositor,
    COMPOSITOR_PT_cinematic_panel,
    VIEW3D_PT_cinematic_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.cinematic_settings = bpy.props.PointerProperty(type=CinematicSettings)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "cinematic_settings"):
        del bpy.types.Scene.cinematic_settings

if __name__ == "__main__":
    register()
