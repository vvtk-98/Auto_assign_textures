import os
import unreal


def find_texture_by_type(shader_name, texture_type):
    if shader_name.upper().endswith("_SG"):
        shader_name = shader_name[:-3]

    unreal.log(f"Looking for textures with shader name: {shader_name} and '{texture_type}' in the name")
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

    filter = unreal.ARFilter(
        class_names=["Texture2D"],
        recursive_classes=True
    )

    all_textures = asset_registry.get_assets(filter)
    unreal.log(f"Searching through {len(all_textures)} textures in the project")

    for texture_data in all_textures:
        asset_name = str(texture_data.asset_name)
        package_path = str(texture_data.package_path)

        if asset_name.lower().startswith(f"{shader_name.lower()}_sg_{texture_type.lower()}"):
            full_path = f"{package_path}/{asset_name}"
            unreal.log(f"Found exact matching {texture_type} texture: {full_path}")
            return full_path

    unreal.log(f"No matching {texture_type} texture found via asset registry, trying filesystem search")
    content_dir = unreal.Paths.project_content_dir()
    unreal.log(f"Project content directory: {content_dir}")

    matching_textures = []
    for root, dirs, files in os.walk(content_dir):
        if "Games" in dirs:
            dirs.remove("Games")

        for file in files:
            if file.lower().endswith((".uasset", ".png", ".tga", ".jpg", ".jpeg")):
                file_without_ext = os.path.splitext(file)[0]

                if file_without_ext.lower().startswith(f"{shader_name.lower()}_sg_{texture_type.lower()}"):
                    full_path = os.path.join(root, file)
                    matching_textures.append(full_path)
                    unreal.log(f"Found exact matching {texture_type} texture via filesystem: {full_path}")
                    break

    if matching_textures:
        rel_path = os.path.relpath(matching_textures[0], content_dir)
        base_name = os.path.splitext(rel_path)[0]
        if base_name.lower().endswith((".png", ".tga", ".jpg", ".jpeg")):
            base_name = os.path.splitext(base_name)[0]
        normalized_path = base_name.replace('\\', '/')
        asset_path = f"/Game/{normalized_path}"
        unreal.log(f"Converting to asset path: {asset_path}")
        return asset_path

    unreal.log_warning(f"No {texture_type} texture found for shader '{shader_name}' in any variation")
    return None


def find_basecolor_texture(shader_name):
    return find_texture_by_type(shader_name, "BaseColor")


def find_normal_texture(shader_name):
    return find_texture_by_type(shader_name, "Normal")


def find_orm_texture(shader_name):
    texture_path = find_texture_by_type(shader_name, "OcclusionRoughnessMetallic")

    if not texture_path:
        texture_path = find_texture_by_type(shader_name, "ORM")

    if not texture_path:
        texture_path = find_texture_by_type(shader_name, "AmbientOcclusion")

    return texture_path


def load_texture_asset(texture_path):
    if not texture_path:
        return None

    try:
        texture_asset = unreal.load_asset(texture_path)
        if texture_asset:
            unreal.log(f"Successfully loaded texture: {texture_path}")
            return texture_asset
        else:
            unreal.log_warning(f"Failed to load texture at path: {texture_path}")
    except Exception as e:
        unreal.log_error(f"Error loading texture: {str(e)}")

        unreal.log("Trying alternative texture loading approach...")
        try:
            asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
            asset_data = asset_registry.get_asset_by_object_path(texture_path)

            if asset_data:
                texture_asset = unreal.load_asset(str(asset_data.package_name))
                if texture_asset:
                    unreal.log(f"Successfully loaded texture using alternative method: {texture_path}")
                    return texture_asset
                else:
                    unreal.log_warning("Alternative texture loading failed")
            else:
                unreal.log_warning(f"Could not find asset data for: {texture_path}")
        except Exception as e2:
            unreal.log_error(f"Alternative texture loading failed with error: {str(e2)}")

    return None


def configure_texture_settings(texture_asset, is_orm=False):
    if not texture_asset:
        return False

    try:
        if is_orm:
            texture_asset.set_editor_property("srgb", False)
            unreal.log(f"Disabled sRGB for ORM texture")
            return True

    except Exception as e:
        unreal.log_error(f"Error configuring texture settings: {str(e)}")
        return False

    return True


def add_texture_to_selected_material():
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected_assets or len(selected_assets) == 0:
        unreal.log_error("No assets selected in the content browser")
        return None

    processed_materials = []
    materials_found = False

    for asset in selected_assets:
        if isinstance(asset, unreal.Material):
            materials_found = True
            material = asset

            unreal.log(f"Processing material: {material.get_name()}")

            material_name = material.get_name()
            shader_name = material_name.split("_SG")[0] if "_SG" in material_name else material_name

            material_edit_lib = unreal.MaterialEditingLibrary

            texture_path = find_basecolor_texture(shader_name)
            if texture_path:
                basecolor_sample = material_edit_lib.create_material_expression(material,
                                                                                unreal.MaterialExpressionTextureSample)
                basecolor_sample.material_expression_editor_x = -400
                basecolor_sample.material_expression_editor_y = 0
                texture_asset = load_texture_asset(texture_path)
                if texture_asset:
                    basecolor_sample.set_editor_property("texture", texture_asset)
                    material_edit_lib.connect_material_property(basecolor_sample, "RGB",
                                                                unreal.MaterialProperty.MP_BASE_COLOR)
                    unreal.log(f"Added BaseColor texture to material '{material.get_name()}'")
                else:
                    unreal.log_warning(f"Failed to add BaseColor texture to material")
            else:
                unreal.log_warning(f"No texture with '{shader_name}' and 'BaseColor' found")

            normal_path = find_normal_texture(shader_name)
            if normal_path:
                normal_sample = material_edit_lib.create_material_expression(material,
                                                                             unreal.MaterialExpressionTextureSample)
                normal_sample.material_expression_editor_x = -400
                normal_sample.material_expression_editor_y = 200
                normal_sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
                normal_asset = load_texture_asset(normal_path)
                if normal_asset:
                    normal_sample.set_editor_property("texture", normal_asset)
                    material_edit_lib.connect_material_property(normal_sample, "RGB", unreal.MaterialProperty.MP_NORMAL)
                    unreal.log(f"Added Normal texture to material '{material.get_name()}'")
                else:
                    unreal.log_warning(f"Failed to add Normal texture to material")
            else:
                unreal.log_warning(f"No texture with '{shader_name}' and 'Normal' found")

            orm_path = find_orm_texture(shader_name)
            if orm_path:
                orm_sample = material_edit_lib.create_material_expression(material,
                                                                          unreal.MaterialExpressionTextureSample)
                orm_sample.material_expression_editor_x = -400
                orm_sample.material_expression_editor_y = 400
                orm_asset = load_texture_asset(orm_path)
                if orm_asset:
                    configure_texture_settings(orm_asset, is_orm=True)
                    orm_sample.set_editor_property("texture", orm_asset)
                    material_edit_lib.connect_material_property(orm_sample, "R",
                                                                unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
                    material_edit_lib.connect_material_property(orm_sample, "G", unreal.MaterialProperty.MP_ROUGHNESS)
                    material_edit_lib.connect_material_property(orm_sample, "B", unreal.MaterialProperty.MP_METALLIC)
                    unreal.log(f"Added ORM texture to material '{material.get_name()}'")
                else:
                    unreal.log_warning(f"Failed to add ORM texture to material")
            else:
                unreal.log_warning(
                    f"No texture with '{shader_name}' and 'ORM/OcclusionRoughnessMetallic/AmbientOcclusion' found")

            material_edit_lib.recompile_material(material)
            unreal.log(f"Finished processing material '{material.get_name()}'")
            processed_materials.append(material)

    if not materials_found:
        unreal.log_error("No materials found in the selection")
        return None

    unreal.log(f"Processed {len(processed_materials)} materials in total")
    return processed_materials


if __name__ == "__main__":
    add_texture_to_selected_material()