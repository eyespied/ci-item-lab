using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Xml.Linq;
using HarmonyLib;
using TaleWorlds.Core;
using TaleWorlds.Engine;
using TaleWorlds.MountAndBlade.View;
using Path = System.IO.Path;
using System.Linq;
using TaleWorlds.Library;

namespace CIItemLab
{
    internal static class ItemColors
    {
        private static readonly Dictionary<string, uint[]> Colors = new Dictionary<string, uint[]>();
        private static readonly HashSet<string> Shared = new HashSet<string>();
        private static readonly Dictionary<string, uint[]> Profiles = new Dictionary<string, uint[]>();
        private static readonly Dictionary<string, string> ProfileNames = new Dictionary<string, string>();
        private static string _selected = "GIB";
        private static Harmony _harmony;
        internal static void Initialize()
        {
            var bin = Path.GetDirectoryName(typeof(ItemColors).Assembly.Location);
            var path = Path.GetFullPath(Path.Combine(bin, "..", "..", "ModuleData", "lab_item_colors.xml"));
            var root = XDocument.Load(path).Root;
            foreach (var e in root.Elements("Item"))
                Colors[(string)e.Attribute("id")] = new[] { Convert.ToUInt32((string)e.Attribute("color1"), 16), Convert.ToUInt32((string)e.Attribute("color2"), 16) };
            foreach (var e in root.Elements("SharedItem")) Shared.Add((string)e.Attribute("id"));
            foreach (var e in root.Elements("Clan"))
            {
                var id = (string)e.Attribute("id");
                Profiles[id] = new[] { Convert.ToUInt32((string)e.Attribute("color1"), 16), Convert.ToUInt32((string)e.Attribute("color2"), 16) };
                ProfileNames[id] = (string)e.Attribute("name");
            }
            _harmony = new Harmony("local.ci.itemlab.colors");
            var postfix = new HarmonyMethod(typeof(ItemColors).GetMethod(nameof(Apply), BindingFlags.Static | BindingFlags.NonPublic));
            foreach (var method in typeof(ItemObjectViewExtensions).GetMethods(BindingFlags.Static | BindingFlags.Public))
                if (method.Name == "GetMultiMeshCopy" || method.Name == "GetMultiMeshCopyWithGenderData")
                    _harmony.Patch(method, postfix: postfix);
        }
        internal static void Unload() { _harmony?.UnpatchAll("local.ci.itemlab.colors"); Colors.Clear(); }
        private static void Apply(ItemObject itemObject, MetaMesh __result)
        {
            if (itemObject == null || __result == null) return;
            // Raw asset tests do not have an authoritative multiplayer material setup.
            // Preserve their original shader and textures instead of imposing a mask shader.
            if (itemObject.StringId.StartsWith("cilab_asset_", StringComparison.Ordinal)
                || itemObject.StringId.StartsWith("cilab_piece_test_", StringComparison.Ordinal)) return;
            var palette = Palette(itemObject);
            if (palette == null) return;
            // Retain the material's declared shader. A color override must not turn an
            // arbitrary material into a double-colormap shader without its required mask.
            for (int i = 0; i < __result.MeshCount; i++)
            {
                var mesh = __result.GetMeshAtIndex(i);
                if (mesh == null || mesh.HasTag("no_team_color")) continue;
                var material = mesh.GetMaterial();
                var shader = material?.GetShader();
                if (shader == null) continue;
                var mask = shader.GetMaterialShaderFlagMask("use_double_colormap_with_mask_texture");
                // Ordinary metal shaders multiply the entire albedo by Mesh.Color.
                // Only tint materials that already declare the masked color path.
                if (mask == 0 || (material.GetShaderFlags() & (ulong)mask) == 0) continue;
                mesh.Color = palette[0];
                mesh.Color2 = palette[1];
            }
        }
        internal static uint[] PaletteFor(Equipment equipment)
        {
            foreach (var slot in new[] { EquipmentIndex.Head, EquipmentIndex.Body, EquipmentIndex.Cape })
                if (equipment[slot].Item != null && Colors.TryGetValue(equipment[slot].Item.StringId, out var palette)) return palette;
            foreach (var slot in new[] { EquipmentIndex.Head, EquipmentIndex.Body, EquipmentIndex.Cape })
                if (equipment[slot].Item != null && Palette(equipment[slot].Item) is uint[] palette) return palette;
            return null;
        }
        private static uint[] Palette(ItemObject item)
        {
            if (item.StringId.StartsWith("cilab_asset_", StringComparison.Ordinal)
                || item.StringId.StartsWith("cilab_piece_test_", StringComparison.Ordinal)) return null;
            if (Colors.TryGetValue(item.StringId, out var palette)) return palette;
            if (item.StringId.StartsWith("cilab_") && (Shared.Contains(item.StringId) || item.IsUsingTeamColor)
                && Profiles.TryGetValue(_selected, out palette)) return palette;
            return null;
        }
        internal static void ShowProfiles()
        {
            var choices=Profiles.Keys.OrderBy(id=>ProfileNames[id]).Select(id=>new InquiryElement(id,ProfileNames[id]+" ["+id+"]",null)).ToList();
            MBInformationManager.ShowMultiSelectionInquiry(new MultiSelectionInquiryData("CI color profile",
                "Choose colors for shared/team-colored items. Dedicated clan items retain their own palette. Close and reopen F8 after choosing.",
                choices,true,1,1,"Use colors","Cancel",selection=>
                { _selected=(string)selection[0].Identifier; InformationManager.DisplayMessage(new InformationMessage("CI shared-item palette: "+ProfileNames[_selected])); },selection=>{},isSeachAvailable:true),true);
        }
    }
}
