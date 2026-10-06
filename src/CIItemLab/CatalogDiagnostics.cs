using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using TaleWorlds.ObjectSystem;
using HarmonyLib;
using TaleWorlds.Core;
using TaleWorlds.CampaignSystem.Inventory;
using TaleWorlds.CampaignSystem.ViewModelCollection.Inventory;

namespace CIItemLab
{
    internal static class CatalogDiagnostics
    {
        private static Harmony _harmony;
        private static readonly HashSet<string> Quarantined = new HashSet<string>
        { "cilab_asset_bre_kettlehelm_2", "cilab_asset_casco", "cilab_asset_tv_aserai_lord_helmet_h" };
        internal static bool IsQuarantined(ItemObject item) => item != null && Quarantined.Contains(item.StringId);
        internal static void Initialize()
        {
            _harmony = new Harmony("local.ci.itemlab.catalog");
            _harmony.Patch(AccessTools.Method(typeof(SPInventoryVM), "InitializeInventory"),
                postfix: new HarmonyMethod(typeof(CatalogDiagnostics), nameof(AfterInitialize)));
            _harmony.Patch(AccessTools.Method(typeof(SPInventoryVM), "UpdateFilteredStatusOfItem"),
                postfix: new HarmonyMethod(typeof(CatalogDiagnostics), nameof(AfterFilter)));
        }
        internal static void Unload() => _harmony?.UnpatchAll("local.ci.itemlab.catalog");
        private static void AfterFilter(SPInventoryVM __instance, SPItemVM item,
            InventoryLogic ____inventoryLogic, Dictionary<SPInventoryVM.Filters, List<int>> ____filters)
        {
            if (____inventoryLogic?.LeftRosterName?.ToString() != "CI Item Lab - All items") return;
            var search = item.InventorySide == InventoryLogic.InventorySide.OtherInventory
                ? __instance.LeftSearchText : __instance.RightSearchText;
            var categoryMatches = ____filters[(SPInventoryVM.Filters)__instance.ActiveFilterIndex].Contains(item.TypeId);
            item.IsFiltered = !categoryMatches || (!string.IsNullOrWhiteSpace(search) &&
                (item.ItemDescription ?? "").IndexOf(search.Trim(), StringComparison.OrdinalIgnoreCase) < 0);
        }
        private static void AfterInitialize(SPInventoryVM __instance, InventoryLogic ____inventoryLogic)
        {
            if (____inventoryLogic?.LeftRosterName?.ToString() != "CI Item Lab - All items") return;
            // Initialize the lab catalog explicitly instead of inheriting inventory UI state.
            __instance.LeftSearchText = "";
            __instance.ExecuteFilterNone();
            Write("view.txt", "Roster rows: " + __instance.LeftItemListVM.Count +
                "\nVisible rows: " + __instance.LeftItemListVM.Count(i => !i.IsFiltered) +
                "\n" + string.Join("\n", __instance.LeftItemListVM.GroupBy(i => i.TypeId)
                    .Select(g => "Type " + g.Key + ": " + g.Count())));
        }
        internal static void RecordItems(List<ItemObject> items)
        {
            Write("items.tsv", "id\ttype\tready\tname\n" + string.Join("\n", items.Select(i =>
                i.StringId + "\t" + i.Type + "\t" + i.IsReady + "\t" + i.Name)));
        }
        internal static void LoadMissingItems()
        {
            var data = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(typeof(CatalogDiagnostics).Assembly.Location),
                "..", "..", "ModuleData", "labitems"));
            var errors = new List<string>();
            int expected = 0, recovered = 0;
            foreach (var file in Directory.GetFiles(data, "*.xml").OrderBy(f => f))
            {
                var doc = new XmlDocument(); doc.Load(file);
                foreach (XmlNode node in doc.DocumentElement.ChildNodes)
                {
                    if (node.NodeType != XmlNodeType.Element) continue;
                    var id = node.Attributes["id"]?.Value;
                    if (id == null) continue;
                    expected++;
                    var existing = MBObjectManager.Instance.GetObject<ItemObject>(id);
                    if (existing != null && existing.IsReady && existing.ItemComponent != null) continue;
                    try
                    {
                        var item = (ItemObject)MBObjectManager.Instance.CreateObjectFromXmlNode(node, "Item");
                        if (item == null || item.ItemComponent == null) throw new InvalidOperationException("No usable item component");
                        recovered++;
                    }
                    catch (Exception ex) { errors.Add(id + "\t" + ex); }
                }
            }
            Write("loading.txt", "Expected: " + expected + "\nRecovered: " + recovered + "\nFailures: " + errors.Count + "\n" + string.Join("\n", errors));
            if (errors.Count > 0) TaleWorlds.Library.InformationManager.DisplayMessage(
                new TaleWorlds.Library.InformationMessage("CI catalog: " + errors.Count + " definitions failed; details recorded in loading.txt."));
        }
        private static void Write(string name, string text)
        {
            try
            {
                var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                    "Mount and Blade II Bannerlord", "CIItemLab", "diagnostics");
                Directory.CreateDirectory(dir);
                File.WriteAllText(Path.Combine(dir, name), DateTime.Now.ToString("O") + "\n" + text);
            }
            catch { /* Diagnostics must never interrupt the catalog. */ }
        }
    }
}
