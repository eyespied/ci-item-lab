using System;
using System.Collections.Generic;
using System.Linq;
using Helpers;
using TaleWorlds.CampaignSystem;
using TaleWorlds.CampaignSystem.GameState;
using TaleWorlds.CampaignSystem.Party;
using TaleWorlds.CampaignSystem.Roster;
using TaleWorlds.Core;
using TaleWorlds.Core.ImageIdentifiers;
using TaleWorlds.InputSystem;
using TaleWorlds.Library;
using TaleWorlds.MountAndBlade;
using TaleWorlds.ObjectSystem;
using TaleWorlds.Localization;

namespace CIItemLab
{
    public sealed class SubModule : MBSubModuleBase
    {
        protected override void OnSubModuleLoad()
        {
            base.OnSubModuleLoad();
            CatalogDiagnostics.Initialize();
            try { ItemColors.Initialize(); }
            catch (Exception ex) { Message("CI Item Lab color setup: " + ex.Message); }
        }
        protected override void OnSubModuleUnloaded()
        { CatalogDiagnostics.Unload(); ItemColors.Unload(); base.OnSubModuleUnloaded(); }
        private Action _pending;
        private bool _welcomed;
        private string _lastSearch = "";
        private string _lastArena = "arena_empire_a";
        private int _arenaMode;

        protected override void OnApplicationTick(float dt)
        {
            base.OnApplicationTick(dt);
            var arena = Mission.Current?.GetMissionBehavior<LabArenaLogic>();
            if (arena != null)
            {
                if (InformationManager.IsAnyInquiryActive()) return;
                if (Input.IsKeyPressed(InputKey.F10)) Mission.Current.EndMission();
                else if (Input.IsKeyPressed(InputKey.F8))
                { _pending = OpenCatalog; Mission.Current.EndMission(); }
                else if (Input.IsKeyPressed(InputKey.F9))
                { _pending = () => LabArena.Open(_lastArena, _arenaMode); Mission.Current.EndMission(); }
                return;
            }
            if (Campaign.Current == null) { _welcomed = false; _pending = null; return; }
            var map = Game.Current?.GameStateManager?.ActiveState as MapState;
            if (map == null || map.MapConversationActive || map.IsSimulationActive || Mission.Current != null)
                return;
            if (!_welcomed)
            {
                _welcomed = true;
                Message("CI Item Lab: F8 = full item catalog; F9 = test arena; Ctrl+F8 = ID search.");
            }
            if (InformationManager.IsAnyInquiryActive()) return;
            try
            {
                if (_pending != null)
                {
                    var next = _pending; _pending = null; next();
                }
                else if (Input.IsKeyPressed(InputKey.F8))
                {
                    if (Input.IsKeyDown(InputKey.LeftControl) || Input.IsKeyDown(InputKey.RightControl)) ShowSearch();
                    else OpenCatalog();
                }
                else if (Input.IsKeyPressed(InputKey.F9)) ShowArenas();
                else if (Input.IsKeyPressed(InputKey.F7)) ItemColors.ShowProfiles();
            }
            catch (Exception ex)
            {
                _pending = null;
                Message("CI Item Lab: " + ex.Message);
            }
        }

        private static void OpenCatalog()
        {
            if (MobileParty.MainParty == null) return;
            CatalogDiagnostics.LoadMissingItems();
            var catalog = new ItemRoster();
            var items = MBObjectManager.Instance.GetObjectTypeList<ItemObject>()
                .Where(i => IsLab(i) && !CatalogDiagnostics.IsQuarantined(i)).OrderBy(i => i.Name?.ToString()).ToList();
            foreach (var item in items) catalog.AddToCounts(item, 10);
            CatalogDiagnostics.RecordItems(items);
            Message("CI catalog: " + items.Count + " items on the left. Search by category, pack, name or original ID. F9 on the map = arena.");
            InventoryScreenHelper.OpenScreenAsReceiveItems(catalog, new TextObject("CI Item Lab - All items"));
        }

        private void ShowArenas()
        {
            var choices = new List<InquiryElement>
            {
                new InquiryElement("arena_empire_a", "Imperial arena", null),
                new InquiryElement("arena_vlandia_a", "Vlandian arena", null),
                new InquiryElement("arena_battania_a", "Battanian arena", null),
                new InquiryElement("arena_sturgia_a", "Sturgian arena", null),
                new InquiryElement("arena_aserai_a", "Aserai arena", null),
                new InquiryElement("arena_khuzait_a", "Khuzait arena", null),
                new InquiryElement("vlandia_tavern_interior_a", "Tavern - Vlandian", null),
                new InquiryElement("empire_interior_tavern_a", "Tavern - Imperial", null),
                new InquiryElement("aserai_tavern_interior", "Tavern - Aserai", null),
                new InquiryElement("sturgia_house_b_interior_tavern", "Tavern - Sturgian", null),
                new InquiryElement("battania_town_house_a_interior_a_tavern", "Tavern - Battanian", null),
                new InquiryElement("khuzait_tavern_a", "Tavern - Khuzait", null),
                new InquiryElement("empire_keep_d_interior", "Keep - Imperial hall", null),
                new InquiryElement("european_castle_keep_a_l3_interior", "Keep - Vlandian great hall", null),
                new InquiryElement("battania_castle_keep_a_l3_interior", "Keep - Battanian hall", null),
                new InquiryElement("aserai_castle_keep_a_l3_interior", "Keep - Aserai hall", null)
            };
            MBInformationManager.ShowMultiSelectionInquiry(new MultiSelectionInquiryData(
                "CI Item Lab - choose a destination", "Arenas for combat; taverns and keeps for exploring and photos. Enter with your battle equipment. Your party stays in place.",
                choices, true, 1, 1, "Next", "Cancel", selected =>
                {
                    _lastArena = (string)selected[0].Identifier;
                    if (_lastArena.StartsWith("arena_")) _pending = ShowArenaModes;
                    else { _arenaMode = 3; _pending = () => LabArena.Open(_lastArena, _arenaMode); }
                }, selected => { }, isSeachAvailable: true), true);
        }

        private void ShowArenaModes()
        {
            var choices = new List<InquiryElement>
            {
                new InquiryElement(0, "Explore - walk or ride, no opponent", null),
                new InquiryElement(1, "Sparring - on foot", null),
                new InquiryElement(2, "Sparring - bring your equipped horse", null)
            };
            MBInformationManager.ShowMultiSelectionInquiry(new MultiSelectionInquiryData(
                "CI Item Lab - test mode", "F8 returns to the item catalog. F9 restarts the round. F10 returns to the map. Sparring is nonlethal.",
                choices, true, 1, 1, "Enter arena", "Cancel", selected =>
                { _arenaMode = (int)selected[0].Identifier; _pending = () => LabArena.Open(_lastArena, _arenaMode); }, selected => { }), true);
        }

        private void ShowSearch()
        {
            InformationManager.ShowTextInquiry(new TextInquiryData(
                "CI Item Lab - search",
                "Search CI items by name, original ID, or type (sword, shield, HeadArmor, etc.). " +
                "Leave blank to browse CI. Prefix all: to include vanilla/other loaded items. " +
                "Enter inventory to open your equipment, or clear to remove unequipped lab items.",
                true, true, "Search", "Cancel", text =>
                {
                    _lastSearch = text ?? "";
                    _pending = () => Search(_lastSearch);
                }, () => { }, defaultInputText: _lastSearch), true);
        }

        private void Search(string query)
        {
            query = query.Trim();
            if (query.Equals("inventory", StringComparison.OrdinalIgnoreCase)) { OpenInventory(); return; }
            if (query.Equals("clear", StringComparison.OrdinalIgnoreCase))
            {
                var roster = MobileParty.MainParty.ItemRoster;
                for (int i = roster.Count - 1; i >= 0; --i)
                {
                    var entry = roster.GetElementCopyAtIndex(i);
                    if (IsLab(entry.EquipmentElement.Item))
                        roster.AddToCounts(entry.EquipmentElement, -entry.Amount);
                }
                Message("Removed unequipped CI lab items from your inventory."); return;
            }
            bool all = query.StartsWith("all:", StringComparison.OrdinalIgnoreCase);
            if (all) query = query.Substring(4).Trim();
            var words = query.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            var matches = MBObjectManager.Instance.GetObjectTypeList<ItemObject>()
                .Where(i => i != null && !CatalogDiagnostics.IsQuarantined(i) && (all || IsLab(i)))
                .Where(i => words.All(w => Contains(i.Name?.ToString(), w) || Contains(i.StringId, w) || Contains(i.ItemType.ToString(), w)))
                .OrderBy(i => i.Name?.ToString()).ThenBy(i => i.StringId).ToList();
            if (matches.Count == 0)
            {
                Message("No matching items. Press Ctrl+F8 and try a shorter name or ID."); return;
            }
            ShowPage(matches, 0);
        }

        private void ShowPage(List<ItemObject> matches, int page)
        {
            const int pageSize = 80;
            var visible = matches.Skip(page * pageSize).Take(pageSize).ToList();
            var choices = visible.Select(i => new InquiryElement(i,
                i.Name + " [" + i.ItemType + "] " + i.StringId.Replace("cilab_", ""),
                new ItemImageIdentifier(i), true,
                "ID: " + i.StringId + " | Weight: " + i.Weight + " | Value: " + i.Value)).ToList();
            if (page > 0) choices.Insert(0, new InquiryElement("previous", "< Previous page", null));
            if ((page + 1) * pageSize < matches.Count) choices.Add(new InquiryElement("next", "Next page >", null));
            MBInformationManager.ShowMultiSelectionInquiry(new MultiSelectionInquiryData(
                "CI Item Lab - " + matches.Count + " matches",
                "Page " + (page + 1) + "/" + ((matches.Count + pageSize - 1) / pageSize) +
                ". Select up to 20 items, then Add & equip. Items are free; no cheat mode needed. " +
                "The search box filters this page. Ctrl+F8 starts a new search across the whole library.",
                choices, true, 1, 20, "Add & equip", "Close", selection =>
                {
                    _pending = () =>
                    {
                        // Navigation entries must be selected alone to prevent ambiguous actions.
                        if (selection.Count == 1 && selection[0].Identifier is string nav)
                        { ShowPage(matches, page + (nav == "next" ? 1 : -1)); return; }
                        var items = selection.Select(e => e.Identifier).OfType<ItemObject>().ToList();
                        if (items.Count == 0) return;
                        foreach (var item in items) MobileParty.MainParty.ItemRoster.AddToCounts(item, 1);
                        Message("Added " + items.Count + " item(s). Equip them in your battle equipment slots.");
                        OpenInventory();
                    };
                }, selection => { }, isSeachAvailable: true), true);
        }

        private static void OpenInventory()
        {
            if (MobileParty.MainParty != null && CharacterObject.PlayerCharacter != null)
                InventoryScreenHelper.OpenScreenAsInventoryOf(MobileParty.MainParty, CharacterObject.PlayerCharacter);
        }
        private static bool IsLab(ItemObject item) => item?.StringId?.StartsWith("cilab_", StringComparison.Ordinal) == true;
        private static bool Contains(string value, string term) => value?.IndexOf(term, StringComparison.OrdinalIgnoreCase) >= 0;
        private static void Message(string text) => InformationManager.DisplayMessage(new InformationMessage(text));
    }
}
